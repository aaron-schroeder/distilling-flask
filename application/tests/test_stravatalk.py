import datetime
import os
import unittest
from unittest.mock import Mock, patch

from application import stravatalk


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


class TestLive(unittest.TestCase):
  # Maybe this test case launches a browser window to get me to accept
  # permissions first?
  # Then it saves the token as a variable?

  # Separately, maybe that's a special procedure for the tests that
  # involve the live Strava API. I figure here, I can just mock
  # the requests.* calls function-by-function.
  pass


@patch('application.stravatalk.requests.post')
class TestGetToken(unittest.TestCase):
  
  def test_handle_valid_status_code(self, mock_post):
    mock_token = {'a': 1}
    mock_post.return_value = Mock(
      status_code=200,
      json=Mock(return_value=mock_token)
    )
    result = stravatalk.get_token('some_code', CLIENT_ID, CLIENT_SECRET)
    self.assertEqual(result, mock_token)

  def test_handle_bad_status_code(self, mock_post):
    mock_post.return_value = Mock(status_code=500)
    with self.assertRaises(Exception):
      result = stravatalk.get_token('some_code', CLIENT_ID, CLIENT_SECRET)
    

@patch('application.stravatalk.requests.post')
class TestRefreshToken(unittest.TestCase):

  def get_epoch_timestamp(self, seconds):
    return int(
      (datetime.datetime.now() + datetime.timedelta(seconds=seconds)
      ).strftime('%s')
    )
  
  def test_expired(self, mock_post):
    token = {
      'expires_at': self.get_epoch_timestamp(-10),
      'refresh_token': 'some_refresh_token'
    }
    mock_post.return_value = Mock(
      status_code=200,
      json=Mock(return_value={})
    )
    result = stravatalk.refresh_token(token, CLIENT_ID, CLIENT_SECRET)
    mock_post.assert_called_once()
    
  def test_not_expired(self, mock_post):
    token = {
      'expires_at': self.get_epoch_timestamp(10),
    }
    result = stravatalk.refresh_token(token, CLIENT_ID, CLIENT_SECRET)
    self.assertIs(result, token)
    mock_post.assert_not_called()

  def test_handle_bad_status_code(self, mock_post):
    # reminder to accommodate status codes other than 200.
    token = {
      'expires_at': self.get_epoch_timestamp(-10),
      'refresh_token': 'some_refresh_token'
    }
    mock_post.return_value = Mock(status_code=500)
    with self.assertRaises(Exception):
      result = stravatalk.refresh_token(token, CLIENT_ID, CLIENT_SECRET)


@patch(
  'application.stravatalk.requests.get',
  return_value=Mock(
    json=Mock(return_value=['activity1', 'activity2'])
  )
)
class TestGetActivities(unittest.TestCase):
  access_token = 'abcdefg'

  def test_no_kwargs(self, mock_get):
    result = stravatalk.get_activities_json(self.access_token)
    # self.assertEqual(result, mock_json)
    data_arg = mock_get.call_args.kwargs['data']
    self.assertNotIn('page', data_arg)
    self.assertNotIn('per_page', data_arg)

  def test_page(self, mock_get):
    result = stravatalk.get_activities_json(self.access_token, page=2)
    data_arg = mock_get.call_args.kwargs['data']
    self.assertEqual(data_arg['page'], 2)

  def test_limit(self, mock_get):
    result = stravatalk.get_activities_json(self.access_token, limit=5)
    data_arg = mock_get.call_args.kwargs['data']
    self.assertEqual(data_arg['per_page'], 5)

  def test_headers(self, mock_get):
    result = stravatalk.get_activities_json(self.access_token)
    headers_arg = mock_get.call_args.kwargs['headers']
    self.assertEqual(headers_arg['Authorization'], f'Bearer {self.access_token}')


class TestGetActivity(unittest.TestCase):
  # Such a simple function that it feels like testing a constant
  pass


class TestGetActivityStreams(unittest.TestCase):
  # Such a simple function that it feels like testing a constant
  pass


@unittest.skipIf(True, 'Skipping tests that hit the real strava API server')
class TestResponseFormat(unittest.TestCase):
  """TODO: Make or use a TestCase class that sets up a real self.token"""
  
  def test_get_token(self):
    actual = stravatalk.get_token(self.code, CLIENT_ID, CLIENT_SECRET)

    with patch('application.stravatalk.requests.post') as mock_post:
      mock_post.return_value = Mock(
        status_code=200,
        json=Mock(return_value=self.token)
      )
      mocked = stravatalk.get_token(self.code, CLIENT_ID, CLIENT_SECRET)

    self.fail('finish the test')

  def test_refresh_token(self):
    actual = stravatalk.refresh_token(self.token, CLIENT_ID, CLIENT_SECRET)

    with patch('application.stravatalk.requests.post') as mock_post:
      mock_post.return_value = Mock(
        status_code=200,
        json=Mock(return_value=self.token)
      )
      mocked = stravatalk.refresh_token(self.token, CLIENT_ID, CLIENT_SECRET)

    self.fail('finish the test')

  def test_get_activities(self):
    # Call the service to hit the actual API.
    actual = stravatalk.get_activities_json(self.token)

    # Call the service to hit the mocked API.
    with patch(
      'application.stravatalk.requests.get',
      return_value=Mock(
        json=Mock(return_value=['activity1', 'activity2'])
      )
    ) as mock_get:
      mocked = stravatalk.get_activities_json(self.token)  # use dummy token?
      
    # An object from the actual API and an object from the mocked API should
    # have the same data structure.
    # TODO: Check that each element from the mocked structure is found in
    # the expected place in the actual structure.
    # Whether that's a custom function to compare structures (boo) or some
    # sort of validation schema. 
    # assert_list_equal(actual, mocked)

    self.fail('finish the test')

  def test_get_activity(self):
    id = stravatalk.get_activities_json(self.token)[0]['id']
    actual = stravatalk.get_activity_streams_json(id, self.token)

    self.fail('compare to the format of my stored fake data')

  def test_get_activity_streams(self):
    id = stravatalk.get_activities_json(self.token)[0]['id']
    actual = stravatalk.get_activity_streams_json(id, self.token)

    self.fail('compare to the format of my stored fake data')