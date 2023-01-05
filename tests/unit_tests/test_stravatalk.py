import datetime
import os
import unittest
from unittest.mock import Mock, patch

from application import stravatalk


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


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
    data_arg = mock_get.call_args.kwargs['params']
    self.assertNotIn('page', data_arg)
    self.assertNotIn('per_page', data_arg)

  def test_page(self, mock_get):
    result = stravatalk.get_activities_json(self.access_token, page=2)
    data_arg = mock_get.call_args.kwargs['params']
    self.assertEqual(data_arg['page'], 2)

  def test_limit(self, mock_get):
    result = stravatalk.get_activities_json(self.access_token, limit=5)
    data_arg = mock_get.call_args.kwargs['params']
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
