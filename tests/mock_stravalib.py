import json

import stravalib


with open('tests/unit_tests/sample_data/exchange_code_for_token.json', 'r') as f:
  MOCK_TOKEN = json.load(f)


class Client:
  def __init__(self, *args, **kwargs):
    self.access_token = kwargs.pop('access_token', None)

  def exchange_code_for_token(self, code=None, client_id=None, client_secret=None):
    return MOCK_TOKEN

  def refresh_access_token(self, refresh_token=None, client_id=None, client_secret=None):
    return MOCK_TOKEN

  def get_athlete(*args, **kwargs):
    return stravalib.model.Athlete(id=1)

  def get_activities_json(self, limit=None, page=None):
    # TODO: Handle different inputs for `limit` and `page`
    return BatchedResultsIterator()

  def get_activity(self, activity_id):
    with open('tests/unit_tests/sample_data/get_activity.json', 'r') as f:
      data = json.load(f)
    return stravalib.model.Activity(**data)

  def get_activity_streams(self, activity_id, types=None):
    with open('tests/unit_tests/sample_data/get_activity_streams.json', 'r') as f:
      data = json.load(f)
    return {stream['type']: stravalib.model.Stream(**stream) for stream in data}


class BatchedResultsIterator:
  def __init__(self, *args, **kwargs):
    self._page = 1
    self.per_page = 200
    self.limit = None
    self._counter = 0

    self._num_results = 1000

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
        start_date_local='2018-02-20T10:02:13Z',
        distance=10000,
        total_elevation_gain=100,
      )
      self._counter += 1
      return result
