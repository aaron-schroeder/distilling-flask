"""Functions for interacting with the Strava API.

I opted to create my own functions instead of relying on `stravalib`,
as its functionality is more expansive than I require and it is prone
to issues.

"""
import datetime
import json
import os

import requests


def get_access_token(
  code_from_redirect_url,
  client_id, 
  client_secret,
  fname_out='tokens.json'
):
  """Get an access token from a redirect code given by Strava.

  When Strava's Oauth page is shown to the user (me), clicking to grant
  the permissions will cause a redirect to a localhost page. Although
  the page won't show anything (cannot be displayed or whatever), the
  redirected url will have a code as a parameter.

  Args:
    code_from_redirect_url (str): The code that is appended to the 
      redirected url (after granting my app permissions) as a parameter.
    client_id (int or str): The Strava client id of the athlete
      who granted permissions to my app. Generally will be me.
    client_secret (str): The Strava client secret of the athlete
      who granted permissions to my app. Generally will be me.
    fname_out (str): Path to the json file that will be created to
      locally store the token json response.

  Returns:
    str: A fresh access token for use with Strava's API.
  
  """
  # code_from_redirect_url = '52439604cab41d1b3462cde08a2fdee05ca42894'

  resp_token = requests.post(
    url='https://www.strava.com/oauth/token',
    data={
      'client_id': client_id,
      'client_secret': client_secret,
      'code': code_from_redirect_url,
      'grant_type': 'authorization_code'
    }
  )

  return handle_token_response(resp_token, fname_out)


def refresh_access_token(fname, client_id, client_secret):
  """Ensure a fresh access token for interaction with the Strava API.

  Args:
    fname (str): Name of json file where Strava's json response from
      the last token refresh is stored. The json should contain
      keys 'access_token', 'refresh_token', and 'expires_at'.
    client_id (int or str): The Strava client id of the athlete
      associated with the access token.
    client_secret (str): The Strava client secret of the athlete
      associated with the access token.
  
  Returns:
    str: A fresh access token for use with the Strava API.
  
  """
  with open(fname, 'r') as f:
    tokens = json.load(f)
  
  # Check if access_token is expired, and if so, refresh it.
  if datetime.datetime.utcnow() < datetime.datetime.utcfromtimestamp(tokens['expires_at']):
    return tokens['access_token']

  else:
    print('Refreshing expired token')

    resp_token = requests.post(
      url='https://www.strava.com/oauth/token',
      data={
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token'
      }
    )
  
    return handle_token_response(resp_token, fname)


def handle_token_response(resp_token, fname_out):
  if resp_token.status_code == 200:
    # Write the new json to the file.
    tokens = resp_token.json()
    with open(fname_out, 'w') as f:
      json.dump(tokens, f)

    return tokens['access_token']

  # TODO: Print the response when the code is not 200, then throw
  # an exception.


def get_activities_json(access_token, limit=None, page=None):
  """Get a list of activity summary dicts.

  https://developers.strava.com/docs/reference/#api-Activities-getLoggedInAthleteActivities

  `stravalib` implementation for comparison:
  `acts = client.get_activities(limit=10)`

  Args:
    access_token (str): Fresh access token for the Strava API.
    limit (int): Maximum number of activities to be returned in the summary.
      Default None, which will allow Strava API to set the default
      (30 as of this writing).

  Returns:
    list: dicts with summary data for the requested number of the
      activities associated with the athlete whose access_token is used.

  """
  # Get the most recent activities for the athlete.
  # curl -X GET `https://www.strava.com/api/v3/athlete/activities`  \
  #              (?before=&after=&page=&per_page=)
  #      -H "Authorization: Bearer [[token]]"
  # before, after, page, per_page
  data = dict()
  if limit is not None:
    data['per_page'] = limit
  
  if page is not None:
    data['page'] = page

  resp = requests.get(
    'https://www.strava.com/api/v3/athlete/activities',
    data=data,
    headers={'Authorization': f'Bearer {access_token}'}
  )

  return resp.json()


def get_activity_json(activity_id, access_token):
  """Get a dict of summary stats for a given activity.

  https://developers.strava.com/docs/reference/#api-Activities-getActivityById

  `stravalib` implementation for comparison:
  `act = client.get_activity(id)`

  Args:
    activity_id (int): Strava ID for an activity. The requested activity
      must correspond to the athlete associated with the access_token.
    access_token (str): Fresh access token for the Strava API.

  Returns:
    dict: summary data for the requested activity.

  """
  resp = requests.get(
    f'https://www.strava.com/api/v3/activities/{activity_id}',
    headers={'Authorization': f'Bearer {access_token}'}
  )

  return resp.json()


def get_activity_streams_json(activity_id, access_token, types=None):
  """Get streams (time series) for a particular activity.

  https://developers.strava.com/docs/reference/#api-Streams-getActivityStreams

  `stravalib` implementation for reference:
  `streams = client.get_activity_streams(id)`

  Args:
    activity_id (int): Strava ID for an activity. The requested activity
      must correspond to the athlete associated with the access_token.
    access_token (str): Fresh access token for the Strava API.
    types (list(str)): `type`s of the requested activity streams.
      Default None, which will return all available streams.
  
  Returns:
    list: dicts of stream data. `stream['type']` is the field name, and
      `stream['data']` is the time series. Also includes `series_type`,
      `original_size` and `resolution`.

  """

  if types is None:
    types = ['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
             'heartrate', 'cadence', 'watts', 'temp', 'moving',
             'grade_smooth']
  fields = ','.join(types)

  # curl -X GET  \
  # "https://www.strava.com/api/v3/activities/${id}/streams/${fields}"  \
  #      -H "Authorization: Bearer ${access_token}"
  resp = requests.get(
    f'https://www.strava.com/api/v3/activities/{activity_id}/streams/{fields}',
    headers={'Authorization': f'Bearer {access_token}'}
  )

  return resp.json()
