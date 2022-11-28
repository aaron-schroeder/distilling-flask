import json
import unittest
from urllib.parse import urlparse, parse_qs

from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.by import By

from application import stravatalk
from application.tests import mock_stravatalk
from application.tests.util import get_chromedriver


with open('client_secrets.json', 'r') as f:
  client_secrets = json.load(f)
CLIENT_ID = client_secrets['installed']['client_id']
CLIENT_SECRET = client_secrets['installed']['client_secret']


SKIP_REAL_API = True


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
  SKIP_REAL_API,
  'Skipping tests that hit the real strava API server'
)
class TestResponseFormat(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    # TODO: Make or use a TestCase class that sets up a real self.token.
    # Thinking I have to use selenium to accept permissions and get the
    # redirect code.
    # Could it also be like a test that runs first?
    # Checking the format of the returned token?

    browser = get_chromedriver()

    # path = os.path.dirname(os.path.realpath(__file__))
    # with open(os.path.join(path, 'strava_credentials.json'), 'r') as f:
    with open('application/functional_tests/strava_credentials.json', 'r') as f:
      credentials = json.load(f)

    browser.get(
      f'https://www.strava.com/oauth/authorize?'  
      f'client_id={CLIENT_ID}&redirect_uri=http://localhost/'
      f'&approval_prompt=auto&response_type=code&scope=activity:read_all'
    )

    # un = self.wait_for_element(By.ID, 'email')
    un = browser.find_element(By.ID, 'email')
    un.clear()
    un.send_keys(credentials['USERNAME'])
    pw = browser.find_element(By.ID, 'password')
    pw.clear()
    pw.send_keys(credentials['PASSWORD'])
    browser.find_element(By.ID, 'login-button').click()

    try:
      auth_btn = browser.find_element(By.ID, 'authorize')
    except:
      try:
        print(browser.find_element(By.CLASS_NAME, 'alert-message').text)
      except:
        print(browser.page_source)

    # A cookie banner may be in the way
    try:
      auth_btn.click()
    except ElementClickInterceptedException:
      browser.find_element(
        By.CLASS_NAME, 
        'btn-accept-cookie-banner'
      ).click()
      auth_btn.click()

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
