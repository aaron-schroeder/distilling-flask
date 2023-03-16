import json
import os
import unittest
from urllib.parse import urlparse, parse_qs

from flask import url_for
import stravalib

from distilling_flask.util import mock_stravalib
from tests import settings
from tests.util import get_chromedriver, strava_auth_flow


with open('client_secrets.json', 'r') as f:
  client_secrets = json.load(f)
CLIENT_ID = client_secrets['installed']['client_id']
CLIENT_SECRET = client_secrets['installed']['client_secret']


SAMPLE_DATA_DIR = os.path.join(
  os.path.abspath(os.path.dirname(__file__)),
  'sample_data'
)


def validate_structure(mocked, actual):
  """Check if mocked structure is a subset of actual structure.
  
  An object from the actual API and an object from the mocked API should
  have the same data structure.
  """
  if type(mocked) != type(actual):
    print(f'{mocked}: {type(mocked)}')
    print(f'{actual}: {type(actual)}')
    return False

  if isinstance(mocked, dict):
    for key in mocked.keys():
      if key not in actual:
        return False
      elif not validate_structure(mocked[key], actual[key]):
        return False
  elif isinstance(mocked, list) and len(mocked) > 0:
    if not validate_structure(mocked[0], actual[0]):
      return False
  
  return True
  

@unittest.skipIf(
  settings.SKIP_STRAVA_API,
  'Skipping tests that hit the real strava API server'
)
@unittest.skipIf(
  settings.SKIP_STRAVA_OAUTH,
  'This test would pass were I not locked out of my Strava acct. Skipping.'
)
class TestResponseFormat(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    browser = get_chromedriver()
    browser.get(url_for('strava_api.authorize'))
    strava_auth_flow(browser)
    queries = parse_qs(urlparse(browser.current_url).query)
    code = queries['code'][0]
    cls.token = stravalib.Client().exchange_code_for_token(
      code=code, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    browser.quit()

  def save_sample_data(self, data, fname):
    return
    with open(os.path.join(SAMPLE_DATA_DIR, fname), 'w') as f:
      json.dump(data, f)

  def compare_method(self, method_nm, *args, **kwargs):
    """Verify that the structure of the mock response matches the structure
    of the up-to-date response from the API."""
    actual = getattr(stravalib.Client(), method_nm)(*args, **kwargs)
    mocked = getattr(mock_stravalib, method_nm)(*args, **kwargs)
    if not validate_structure(mocked, actual):
      self.save_sample_data(
        actual, 
        f'{method_nm.replace("_json", "")}.json'
      )
      self.fail(
        'Mocked structure not a subset of actual structure.\n'
        'Mocked:\n'
        f'{mocked}\n\n'
        'Actual:\n'
        f'{actual}'
      )

  def test_get_token(self):
    # get the fresh access token created during setUpClass
    actual = self.token
    mocked = mock_stravalib.get_token('some_code', CLIENT_ID, CLIENT_SECRET)
    if not validate_structure(mocked, actual):
      self.fail(
        'Mocked structure not a subset of actual structure.\n'
        'Mocked:\n'
        f'{mocked}\n\n'
        'Actual:\n'
        f'{actual}'
      )

  def test_refresh_token(self):
    # TODO: Don't check the expires_at, just refresh the token.
    self.compare_method('refresh_token', self.token, CLIENT_ID, CLIENT_SECRET)

  def test_get_activities(self):
    self.compare_method('get_activities_json', self.token['access_token'])

  def test_get_activity(self):
    id = stravatalk.get_activities_json(self.token['access_token'])[0]['id']
    self.compare_method('get_activity_json', id, self.token['access_token'])

  def test_get_activity_streams(self):
    id = stravatalk.get_activities_json(self.token['access_token'])[0]['id']
    self.compare_method('get_activity_streams_json', id, self.token['access_token'])
