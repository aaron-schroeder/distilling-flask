import datetime
import json

import stravalib
from stravalib.exc import RateLimitExceeded


with open('tests/unit_tests/sample_data/exchange_code_for_token.json', 'r') as f:
  MOCK_TOKEN = json.load(f)


class DummyClass:
  def __init__(self, *args, **kwargs):
    for key, value in kwargs.items():
      setattr(self, key, value)


def _check_limit_rates(limit):
  if limit['usage'] >= limit['limit']:
    print(f'Rate limit of {limit["limit"]} reached.')
    limit['lastExceeded'] = datetime.datetime.now()
    _raise_rate_limit_exception(limit['time'], limit['limit'])


def _raise_rate_limit_exception(timeout, limit_rate):
  raise RateLimitExceeded(
    f'Rate limit of {limit_rate} exceeded. '
    f'Try again in {timeout} seconds.',
    limit=limit_rate,
    timeout=timeout
  )


def rate_limit(method):
  def decorated_method(client, *args, **kwargs):
    for rule in client.protocol.rate_limiter.rules:
      for limit in rule.rate_limits.values():
        # self._check_limit_time_invalid(limit)
        _check_limit_rates(limit)
    return method(client, *args, **kwargs)
  return decorated_method


class Client:
  _short_limit = 100
  _long_limit = 1000
  _short_usage = 0
  _long_usage = 0
  _activity_count = 100

  def __init__(self, *args, **kwargs):
    self.access_token = kwargs.pop('access_token', None)

  def exchange_code_for_token(self, code=None, client_id=None, client_secret=None):
    return MOCK_TOKEN

  def refresh_access_token(self, refresh_token=None, client_id=None, client_secret=None):
    return MOCK_TOKEN

  @rate_limit
  def get_athlete(self, *args, **kwargs):
    sample_athlete = stravalib.model.Athlete.deserialize(
      # '... tests/unit_tests/sample_data/get_athlete.json ...'
      dict(
        id=1,
        firstname='Sample',
        lastname='Athlete',
        city='Sample City',
        state='Sample State',
        country='Sample Country',
      ),
      bind_client=self
    )
    sample_athlete._stats = stravalib.model.AthleteStats(
      all_run_totals=stravalib.model.ActivityTotals(count=self._activity_count)
    )

    return sample_athlete

  @rate_limit
  def get_activities(self, limit=None):
    o = BatchedResultsIterator()
    o._num_results = min(limit, self._activity_count) if limit else self._activity_count
    return o

  @rate_limit
  def get_activity(self, activity_id):
    with open('tests/unit_tests/sample_data/get_activity.json', 'r') as f:
      data = json.load(f)
    data['id'] = activity_id
    return stravalib.model.Activity(**data)

  @rate_limit
  def get_activity_streams(self, activity_id, types=None):
    with open('tests/unit_tests/sample_data/get_activity_streams.json', 'r') as f:
      data = json.load(f)
    return {stream['type']: stravalib.model.Stream(**stream) for stream in data}

  @property
  def protocol(self):

    return DummyClass(
      rate_limiter=DummyClass(
        rules=[
          DummyClass(
            rate_limits={
              'short': {
                'usage': self._short_usage + 1,
                'limit': self._short_limit,
                'time': 900
              },
              'long': {
                'usage': self._long_usage + 1,
                'limit': self._long_limit,
                'time': 86400
              },
            }
          )
        ]
      )
    )


class BatchedResultsIterator:
  _page = 1
  per_page = 200
  limit = None
  _counter = 0

  _num_results = 1000

  def __iter__(self):
    return self

  def __next__(self):
    if self.limit and self._counter >= self.limit:
      raise StopIteration
    elif self._counter >= self._num_results:
      raise StopIteration
    else:
      result = stravalib.model.Activity(
        id=self._counter + 1,
        name=f'Activity {self._counter + 1}',
        # Throw in a bike ride every once in a while
        type='Run' if self._counter % 5 else 'Ride',
        start_date_local='2018-02-20T10:02:13Z',
        start_date='2018-02-20T10:02:02',
        distance=10000,
        moving_time=3000,
        elapsed_time=3600,
        total_elevation_gain=100,
      )
      self._counter += 1
      return result


class LowLimitClient(Client):
  _short_limit = 100
  _long_limit = 1000
  _short_usage = 0
  _long_usage = 0
  _activity_count = 4


class SimDevClient(Client):
  _short_limit = 100
  _long_limit = 1000
  _short_usage = 0
  _long_usage = 0
  _activity_count = 1100


class SimProdClient(Client):
  _short_limit = 600
  _long_limit = 30000
  _short_usage = 0
  _long_usage = 0
  _activity_count = 1100
