import json


MOCK_TOKEN = {
  "token_type": "Bearer",
  "access_token": "720e40342a74ec60554ac0c67c2eea15d0b83f61",
  "expires_at": 1669278614,
  "expires_in": 21600,
  "refresh_token": "88580d9668f0934546af193d4b3f8214e99f78d9",
  "athlete": {
    "firstname": "Aaron",
    "lastname": "Schroeder"
  }
}


def get_token(code, client_id, client_secret):
  # TODO: See if I need to set a session variable here too. Don't think so.
  return MOCK_TOKEN


def refresh_token(token, client_id, client_secret):
  # TODO: See if I need to check the `expires_at` attr
  return MOCK_TOKEN


def get_activities_json(access_token, limit=None, page=None):
  # TODO: Handle different inputs for `limit` and `page`
  return [
    {
      'id': 1, 
      'name': 'Activity 1', 
      'start_date_local' : '2018-02-20T10:02:13Z',
      'distance': 10000,
      'total_elevation_gain': 100,
    },
    {
      'id': 2, 
      'name': 'Activity 2', 
      'start_date_local' : '2018-02-20T10:02:13Z',
      'distance': 10000,
      'total_elevation_gain': 100,
    },
  ]


def get_activity_json(activity_id, access_token):
  with open('application/tests/sample_data/get_activity.json') as f:
    data = json.load(f)
  return data


def get_activity_streams_json(activity_id, access_token, types=None):
  with open('application/tests/sample_data/get_activity_streams.json') as f:
    data = json.load(f)
  return data
