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
      all_run_totals=stravalib.model.ActivityTotals(count=10)
    )

    return sample_athlete

  def get_activities(self, limit=None):
    o = BatchedResultsIterator()
    o._num_results = limit or 20
    return o

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
        type='Run',
        start_date_local='2018-02-20T10:02:13Z',
        start_date='2018-02-20T10:02:02',
        distance=10000,
        moving_time=3000,
        elapsed_time=3600,
        total_elevation_gain=100,
      )
      self._counter += 1
      return result
