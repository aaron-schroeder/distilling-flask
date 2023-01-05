from unittest.mock import patch

from flask import url_for

from application.models import AdminUser
from .base import FlaskTestCase, LoggedInFlaskTestCase, AuthenticatedFlaskTestCase


# TODO: Use dummy values instead
MOCK_TOKEN = {
  "token_type": "Bearer",
  "access_token": "720e40342a74ec60554ac0c67c2eea15d0b83f61",
  "expires_at": 1669278614,
  "expires_in": 21600,
  "refresh_token": "88580d9668f0934546af193d4b3f8214e99f78d9",
  "athlete": {
    "firstname": "Aaron",
    "lastname": "Schroeder",
    "id": 1,
  }
}


class TestAuthorize(LoggedInFlaskTestCase):
  def test_strava_oauth_authorize(self):
    with self.app.test_request_context():
      rv = self.client.get(url_for('strava_api.authorize'))
    # response should be a redirect
    self.assertEqual(rv.status_code, 302)
    # should redirect to strava's authorization endpoint
    self.assertEqual(
      rv.location.split('?')[0],
      'https://www.strava.com/oauth/authorize'
    )

    # TODO: figure out if more testing is called for


class TestHandleCode(LoggedInFlaskTestCase):

  @patch('application.strava_api.views.stravatalk.get_token')
  def test_strava_oauth_callback(self, mock_get_token):
    mock_get_token.return_value = MOCK_TOKEN

    rv = self.client.get(
      f'{url_for("strava_api.handle_code")}'
      '?code=some_code&scope=read,activity:read_all'
    )

    # Since the scope is accepted correctly, the user is redirected
    # to their strava activity list.
    self.assertEqual(rv.status_code, 302)
    self.assertEqual(rv.location, url_for('route_blueprint.admin_landing'))

    # Next, the external strava api responds to a POST request
    # from my app that includes the code that was previously
    # passed as a parameter on Strava's GET request to the callback url
    # (that strava interaction is mocked out here).
    # Then, the access token returned by strava is stored in the database.
    self.assertEqual(
      AdminUser().strava_account.access_token,
      MOCK_TOKEN['access_token']
    )

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

    rv = self.client.get(
      f'{url_for("strava_api.handle_code")}'
      '?code=some_code&scope=read'
    )

    # When the scope is not accepted (no `activity:read_all`),
    # display a message that tells them to accept the right permissions
    # so my app can function properly.
    self.assertEqual(rv.status_code, 200)
    # self.assertTemplateUsed(rv, 'strava_api/callback.html')
    self.assertIn('permissions', rv.get_data(as_text=True))

  def test_handle_strava_error(self):
    # User clicks `cancel` button when accepting strava permissions, 
    # resulting in strava issuing a GET request to the callback endpoint like:
    rv = self.client.get(
      f'{url_for("strava_api.handle_code")}'
      '?error=access_denied'
    )
    
    # The callback endpoint does not redirect, but displays a message
    # about it being necessary to grant my app access to their strava
    # if they want to use it to analyze their strava data.
    self.assertEqual(rv.status_code, 200)
    # self.assertTemplateUsed(rv, 'strava_api/callback.html')
    self.assertIn('access to', rv.get_data(as_text=True))
    self.assertIn('access_denied', rv.get_data(as_text=True))

  def test_bad_post_response(self):
    # TODO: Handle cases where strava's response to my app's post request
    # does not go as expected.
    # I'm not sure what this would look like, or if it could even happen.
    # I guess the app could make a bad post request, or strava could be down
    # for some reason.
    pass
    

class TestActivityListLoggedIn(LoggedInFlaskTestCase):
  def test_redirect_when_no_token(self):
    self.assertFalse(AdminUser().has_authorized)
    
    response = self.client.get(url_for('strava_api.display_activity_list'))
    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, url_for('strava_api.authorize'))


class TestActivityListAuthorized(AuthenticatedFlaskTestCase):
  @patch('application.strava_api.views.stravatalk.refresh_token')
  @patch('application.strava_api.views.stravatalk.get_activities_json')
  def test_activity_list(self, mock_get_activities, mock_refresh_token):
    
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
    mock_refresh_token.return_value = MOCK_TOKEN
    mock_get_activities.return_value = []

    response = self.client.get('/strava/activities?page=2')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(mock_get_activities.call_args.kwargs['page'], '2')

  def test_no_next_arrow_if_no_next_page(self):
    # Currently would fail.
    # The idea is, if we are at the end of the strava activities,
    # don't provide an option to click over to the next page.
    pass

  def test_token_refreshed_if_expired(self):
    # Might want to just verify that token is passed to refresh_token,
    # and then test refresh_token behavior in test_stravatalk.py
    pass


class TestRevoke(AuthenticatedFlaskTestCase):
  def test_revoke(self):
    self.assertTrue(AdminUser().has_authorized)

    response = self.client.get(url_for('strava_api.revoke'))

    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, url_for('route_blueprint.admin_landing'))

    self.assertFalse(AdminUser().has_authorized)

  def test_revoke_on_strava(self):
    """The user revokes app access at https://www.strava.com/settings/apps"""
    pass