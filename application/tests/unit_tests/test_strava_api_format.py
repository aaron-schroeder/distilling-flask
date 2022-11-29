import json
import unittest
from urllib.parse import urlparse, parse_qs

from application import stravatalk
from application.tests import mock_stravatalk, settings
from application.tests.util import get_chromedriver, strava_auth_flow


with open('client_secrets.json', 'r') as f:
  client_secrets = json.load(f)
CLIENT_ID = client_secrets['installed']['client_id']
CLIENT_SECRET = client_secrets['installed']['client_secret']


def compare_structure(mocked, actual):
  """Check if mocked structure is a subset of actual structure"""
  if type(mocked) != type(actual):
    return False

  if isinstance(mocked, dict):
    for key in mocked.keys():
      if key not in actual:
        return False
      elif not compare_structure(mocked[key], actual[key]):
        return False
  elif isinstance(mocked, list) and len(mocked) > 0:
    if not compare_structure(mocked[0], actual[0]):
      return False
  
  return True
  

@unittest.skipIf(
  settings.SKIP_STRAVA_API,
  'Skipping tests that hit the real strava API server'
)
@unittest.skip('Not fully implemented yet')
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

    # Inspect the redirected url to get the strava auth code
    queries = parse_qs(urlparse(browser.current_url).query)
    code = queries['code'][0]

    cls.token = stravatalk.get_token(code, CLIENT_ID, CLIENT_SECRET)

    browser.quit()

  def has_same_structure(self, mocked, actual):
    if not compare_structure(mocked, actual):
      self.fail(
        'Mocked structure not a subset of actual structure.\n'
        'Mocked:\n'
        f'{mocked}\n\n'
        'Actual:\n'
        f'{actual}'
      )

  def compare_method(self, method_nm):
    """Verify that the structure of the mock response matches the structure
    of the up-to-date response from the API."""
    actual = getattr(stravatalk, method_nm)
    mocked = getattr(mock_stravatalk, method_nm)
    self.has_same_structure(mocked, actual)

  def test_get_token(self):
    # get the fresh access token created during setUpClass
    actual = self.token
    # with patch('application.stravatalk.requests.post') as mock_post:
    #   mock_post.return_value = Mock(
    #     status_code=200,
    #     json=Mock(return_value=self.token)
    #   )
    mocked = mock_stravatalk.get_token('some_code', CLIENT_ID, CLIENT_SECRET)
    self.has_same_structure(mocked, actual)

  @unittest.skip('One test at a time')
  def test_refresh_token(self):
    # TODO: Don't check the expires_at, just refresh the token.
    actual = stravatalk.refresh_token(self.token, CLIENT_ID, CLIENT_SECRET)
    mocked = mock_stravatalk.refresh_token(self.token, CLIENT_ID, CLIENT_SECRET)
    self.has_same_structure(mocked, actual)

  @unittest.skip('One test at a time')
  def test_get_activities(self):
    # Call the service to hit the actual API.
    actual = stravatalk.get_activities_json(self.token)
    # Call the service to hit the mocked API.
    mocked = mock_stravatalk.get_activities_json(self.token)  # use dummy token?
    # An object from the actual API and an object from the mocked API should
    # have the same data structure.
    self.has_same_structure(mocked, actual)

  @unittest.skip('One test at a time')
  def test_get_activity(self):
    id = stravatalk.get_activities_json(self.token)[0]['id']
    actual = stravatalk.get_activity_json(id, self.token)
    mocked_id = mock_stravatalk.get_activities_json(self.token)[0]['id']
    mocked = mock_stravatalk.get_activity_streams_json(mocked_id, self.token)
    self.has_same_structure(mocked, actual)

  @unittest.skip('One test at a time')
  def test_get_activity_streams(self):
    id = stravatalk.get_activities_json(self.token)[0]['id']
    actual = stravatalk.get_activity_streams_json(id, self.token)
    mocked_id = mock_stravatalk.get_activities_json(self.token)[0]['id']
    mocked = mock_stravatalk.get_activity_streams_json(mocked_id, self.token)
    self.has_same_structure(mocked, actual)
