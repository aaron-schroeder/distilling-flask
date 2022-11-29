import json
import os
import unittest
from urllib.parse import urlparse, parse_qs

from application import stravatalk
from application.tests import mock_stravatalk, settings
from application.tests.util import get_chromedriver, strava_auth_flow


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
    browser.get(
      f'https://www.strava.com/oauth/authorize?'  
      f'client_id={CLIENT_ID}&redirect_uri=http://localhost:5000'
      f'&approval_prompt=auto&response_type=code&scope=activity:read_all'
    )
    strava_auth_flow(browser)
    queries = parse_qs(urlparse(browser.current_url).query)
    code = queries['code'][0]
    cls.token = stravatalk.get_token(code, CLIENT_ID, CLIENT_SECRET)
    browser.quit()

  def save_sample_data(self, data, fname):
    with open(os.path.join(SAMPLE_DATA_DIR, fname), 'w') as f:
      json.dump(data, f)

  def compare_method(self, method_nm, *args, **kwargs):
    """Verify that the structure of the mock response matches the structure
    of the up-to-date response from the API."""
    actual = getattr(stravatalk, method_nm)(*args, **kwargs)
    mocked = getattr(mock_stravatalk, method_nm)(*args, **kwargs)
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
    mocked = mock_stravatalk.get_token('some_code', CLIENT_ID, CLIENT_SECRET)
    self.has_same_structure(mocked, actual)

  def test_refresh_token(self):
    # TODO: Don't check the expires_at, just refresh the token.
    self.compare_method('refresh_token', self.token, CLIENT_ID, CLIENT_SECRET)

  def test_get_activities(self):
    self.compare_method('get_activities', self.token['access_token'])

  def test_get_activity(self):
    id = stravatalk.get_activities_json(self.token['access_token'])[0]['id']
    self.compare_method('get_activity', id, self.token['access_token'])

  def test_get_activity_streams(self):
    id = stravatalk.get_activities_json(self.token['access_token'])[0]['id']
    self.compare_method('get_activity_streams', id, self.token['access_token'])
