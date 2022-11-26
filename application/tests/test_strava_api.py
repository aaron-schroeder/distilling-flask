from unittest.mock import Mock, patch

from flask import url_for

from .base import FlaskTestCase


# TODO: Use dummy values instead
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


class Test(FlaskTestCase):
  
  def test_user_revokes(self):
    """The user revokes app access at https://www.strava.com/settings/apps"""
    pass


class TestAuthorize(FlaskTestCase):
  def test_strava_oauth_authorize(self):
    with self.app.test_request_context():
      rv = self.client.get(url_for('strava_api.authorize'))
    # response should be a redirect
    self.assertEqual(rv.status_code, 302)
    # should redirect to facebook's authorization endpoint
    self.assertEqual(
      rv.location.split('?')[0],
      'https://www.strava.com/oauth/authorize'
    )
    # TODO: figure out if more testing is called for


class TestHandleCode(FlaskTestCase):

  # TODO: Put the post request into a stravatalk function,
  # then mock out that function like so:
  # @patch('application.strava_api.stravatalk.post_func') 
  @patch('application.strava_api.views.requests.post')
  def test_strava_oauth_callback(self, mock_post):
    mock_post.return_value = Mock(
      status_code=200,
      json=Mock(return_value=MOCK_TOKEN)
    )

    callback_url = '/strava/callback?code=some_code&scope=read,activity:read_all'
    rv = self.client.get(callback_url)

    # Since the scope is accepted correctly, the user is redirected
    # to their strava activity list.
    self.assertEqual(rv.status_code, 302)
    self.assertEqual(rv.location, '/strava/activities')

    # Next, the external strava api responds to a POST request
    # from my app that includes the code that was previously
    # passed as a parameter on Strava's GET request to the callback url
    # (that strava interaction is mocked out here).
    # Then, the access token returned by strava is set as a session variable.
    with self.client.session_transaction() as sess:
      self.assertEqual(sess.get('token'), MOCK_TOKEN)

    # TODO, when making user model:
    # # when response is new user, db entry created
    # assert db.session.query(User).count() == 1
    # # when response is existing user, no entry added
    # mock_post.json.return_value = {'first_name': 'Andy', 'id': '3617923766551'}
    # rv = self.client.get(callback_url)
    # self.assertEqual(
    #   User.query.filter_by(social_id='facebook$3617923766551').count(),
    #   1
    # )
    # # if user's nickname has changed, db entry is updated
    # user = User.query.filter_by(social_id='facebook$3617923766551').first()
    # self.assertEqual(user.nickname, 'Andy')

  def test_handle_insufficient_permissions(self):
    # should be `read,activity:read_all`, but `read` isn't
    # absolutely necessary

    callback_url = '/strava/callback?code=some_code&scope=read'
    rv = self.client.get(callback_url)

    # When the scope is not accepted (no `activity:read_all`),
    # display a message that tells them to accept the right permissions
    # so my app can function properly.
    self.assertEqual(rv.status_code, 200)
    self.assertIn('permissions', rv.get_data(as_text=True))

  def test_handle_strava_error(self):
    # User clicks `cancel` button when accepting strava permissions, 
    # resulting in strava issuing a GET request to the callback endpoint like:
    callback_url = '/strava/callback?error=access_denied'
    rv = self.client.get(callback_url)
    
    # The callback endpoint does not redirect, but displays a message
    # about it being necessary to grant my app access to their strava
    # if they want to use it to analyze their strava data.
    self.assertEqual(rv.status_code, 200)
    self.assertIn('access to', rv.get_data(as_text=True))
    self.assertIn('access_denied', rv.get_data(as_text=True))

  def test_bad_post_response(self):
    # TODO: Handle cases where strava's response to my app's post request
    # does not go as expected.
    # I'm not sure what this would look like, or if it could even happen.
    # I guess the app could make a bad post request, or strava could be down
    # for some reason.
    pass
    

class TestActivityList(FlaskTestCase):
  def test_redirect_when_no_token(self):
    with self.client.session_transaction() as s:
      self.assertIsNone(s.get('token'))
    
    response = self.client.get('/strava/activities')
    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, '/strava/authorize')

  @patch('application.strava_api.views.stravatalk.refresh_token')
  @patch('application.strava_api.views.stravatalk.get_activities_json')
  def test_activity_list(self, mock_get_activities, mock_refresh_token):
    with self.client.session_transaction() as s:
      s['token'] = MOCK_TOKEN
    
    mock_refresh_token.return_value = MOCK_TOKEN
    mock_get_activities.return_value = [
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

    response = self.client.get('/strava/activities')

    self.assertEqual(response.status_code, 200)
    html_data = response.get_data(as_text=True)
    self.assertIn('Activity 1', html_data)
    self.assertIn('Activity 2', html_data)


  @patch('application.strava_api.views.stravatalk.refresh_token')
  @patch('application.strava_api.views.stravatalk.get_activities_json')
  def test_page_two(self, mock_get_activities, mock_refresh_token):
    with self.client.session_transaction() as s:
      s['token'] = MOCK_TOKEN
    
    mock_refresh_token.return_value = MOCK_TOKEN
    mock_get_activities.return_value = []
    response = self.client.get('/strava/activities?page=2')
    
    self.assertEqual(response.status_code, 200)
    self.assertIn({'page': '2'}, mock_get_activities.call_args)

  def test_no_next_arrow_if_no_next_page(self):
    # Currently would fail.
    # The idea is, if we are at the end of the strava activities,
    # don't provide an option to click over to the next page.
    pass

  def test_token_refreshed_if_expired(self):
    # Might want to just verify that token is passed to refresh_token,
    # and then test refresh_token behavior in test_stravatalk.py
    pass


class TestLogout(FlaskTestCase):
  def test(self):
    with self.client.session_transaction() as sess:
      self.assertIsNone(sess.get('token', None))
      sess['token'] = MOCK_TOKEN

    response = self.client.get('/strava/logout')

    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, '/strava/authorize')

    with self.client.session_transaction() as sess:
      self.assertIsNone(sess.get('token', None))
