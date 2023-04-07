import datetime
import math
import os
import pickle
from urllib.parse import urlencode, urljoin, urlparse, parse_qsl

import requests
from flask import current_app
import warnings


class StravaClientBase:
  _base = ''

  def __init__(self, client_id=None, client_secret=None, access_token=None):
    self.access_token = access_token
    self.client_id = client_id
    self.client_secret = client_secret

  def build_url(self, relative_url, **params):
    url = os.path.join(self._base, relative_url.strip('/'))
    url_parts = urlparse(url)
    query = dict(parse_qsl(url_parts.query))
    query.update(params)
    return url_parts._replace(query=urlencode(query)).geturl()


class StravaOauthClient(StravaClientBase):
  _base = 'https://www.strava.com/oauth'

  def post(self, relative_url, **kwargs):
    params = {'client_id': self.client_id,
              'client_secret': self.client_secret}
    params.update(kwargs)
    r = requests.post(self.build_url(relative_url), data=params)
    # if current_app.config.get('PICKLE_API_RESPONSES', False):
    #   # save the response 
    #   fname = '_'.join(relative_url.strip('/').split('/')) + '.pickle'
    #   with open (fname, 'ab') as f:
    #     pickle.dump(r, f)
    return r


class StravaApiClient(StravaClientBase):
  _base = 'https://www.strava.com/api/v3'

  def get(self, relative_url, **kwargs):
    r = requests.get(self.build_url(relative_url, **kwargs),
                     params={'access_token': self.access_token})
    
    # This could interact with a response at any point; it doesn't
    # have to happen inside the client, at least in this configuration.
    monitor = StravaRateLimitMonitor(r)
    monitor.check_status()  # right now this just prints stuff and returns
    
    # if current_app.config.get('PICKLE_API_RESPONSES', False):
    #   # save the response 
    #   fname = '_'.join(relative_url.strip('/').split('/')) + '.pickle'
    #   with open (fname, 'ab') as f:
    #     pickle.dump(r, f)
    
    return r


class StravaRateLimitMonitor:
  """
  Rate-limiting stuff

  > An application's 15-minute limit is reset at natural 15-minute intervals
    corresponding to 0, 15, 30 and 45 minutes after the hour. The daily limit
    resets at midnight UTC. Requests exceeding the limit will return 
    429 Too Many Requests along with a JSON error message. 
    Note that requests violating the short term limit will still count toward
    the long term limit.

    Successful response headers:
    ```
    HTTP/1.1 200 OK
    Content-Type: application/json; charset=utf-8
    Date: Tue, 10 Oct 2020 20:11:01 GMT
    X-Ratelimit-Limit: 600,30000
    X-Ratelimit-Usage: 314,27536
    ```

    Rate-limited response headers:
    ```
    HTTP/1.1 429 Too Many Requests
    Content-Type: application/json; charset=utf-8
    Date: Tue, 10 Oct 2020 20:11:05 GMT
    X-Ratelimit-Limit: 600,30000
    X-Ratelimit-Usage: 692,29300
    ```

  Ref:
    https://developers.strava.com/docs/rate-limits/
  """
  def __init__(self, response, ignore_warnings=False):
    self.response = response
    limit_header = self.response.headers.get('X-Ratelimit-Limit')
    usage_header = self.response.headers.get('X-Ratelimit-Usage')
    if not limit_header or not usage_header:
      raise ValueError
    self.limits = [int(v) for v in limit_header.split(',')]
    self.usages = [int(v) for v in usage_header.split(',')]
    if not ignore_warnings:
      if (n_lim:= len(self.limits)) != 2:
        warnings.warn(f'The Strava API response header specifies a different '
                      f'number of rate limits ({n_lim}) than expected (2).')
      if (n_use:= len(self.usages)) != 2:
        warnings.warn(f'The Strava API response header specifies a different '
                      f'number of rate limits ({n_lim}) and usages ({n_use}).')

  def check_status(self):
    if self.response.status_code == 429:
      # Indicates this response doesn't contain api data.
      print('Response status code 429: indicates a Strava API rate limit '
            'has been exceeded (or maybe just reached?).')
      # print(self.response.json())
    elif self.response.status_code == 401:
      print('Response status code 401: Strava API did not accept the '
            ' access token it received.')
      # print(self.response.json())
    elif (other_code := self.response.status_code) != 200:
      print(f'Unexpected status code {other_code}.')
      # print(self.response.content)
    
    for usage, limit in zip(self.usages, self.limits):
      if usage == limit:
        # This is actually fine, but we should not make more requests
        # before the limit is reset.
        print(f'Response headers indicate that an API rate limit has been '
              f'reached ({usage} = {limit}).')
      elif usage > limit:
        # Indicates this response doesn't contain api data.
        print('Response headers indicate that an API rate limit has been exceeded '
             f'({usage} > {limit}).')

  def estimate_retry_time(self):
    now = datetime.datetime.utcnow()
    if self.usages[0] > self.limits[0]:
      # Time til next quarter hour
      return datetime.timedelta(minutes=((now.minute - now.second / 60) % 15))
    elif self.usages[1] > self.limits[1]:
      # Time til next utc midnight
      return datetime.datetime(now.year, now.month, now.day + 1) - now

  def estimate_max_rate(self, minutes_to_reset):
    rate_hourly_max = min(
      (self.limits[0] - 5) / (0.25 * 3),
      (self.limits[1] - 5) / (24 * 3)
    )
    return math.floor(rate_hourly_max * minutes_to_reset / 60.0)