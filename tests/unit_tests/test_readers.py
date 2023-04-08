import json
import unittest

from distilling_flask.util.readers import from_strava_streams


with open('tests/unit_tests/sample_data/get_activity_streams.json', 'r') as f:
  stream_data = json.load(f)

class FromStravaStreamsTest(unittest.TestCase):
  def test_basic_cols_exist(self):
    result = from_strava_streams(stream_data)
    for col in ['time', 'speed', 'grade', 'distance']:
      self.assertIn(col, result.columns)