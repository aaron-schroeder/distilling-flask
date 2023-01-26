from unittest.mock import Mock, patch

from flask import url_for
import stravalib

from application.models import db, AdminUser, StravaAccount
from application.util.mock_stravalib import MOCK_TOKEN
from .base import LoggedInFlaskTestCase, AuthenticatedFlaskTestCase


class TestAuthorize(LoggedInFlaskTestCase):
  def test_strava_oauth_authorize(self):
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

  # def setUp(self):
  #   self.mock_stravalib_client = mock_stravalib.Client()
  
  # @patch('stravalib.Client', mock_stravalib.Client)
  @patch('stravalib.Client.get_athlete')
  @patch('stravalib.Client.exchange_code_for_token')
  @patch('stravalib.Client.refresh_access_token')
  def test_strava_oauth_callback(self, mock_refresh_access_token, mock_exchange_code_for_token, mock_get_athlete):
    # mock_strava_api.get('/activities/{id}', response_update={'id': test_activity_id})
    # self.mock_stravalib_client.get_token(response_update={''})
    mock_refresh_access_token.return_value = MOCK_TOKEN
    mock_exchange_code_for_token.return_value = MOCK_TOKEN
    mock_get_athlete.return_value = Mock(id=1)

    rv = self.client.get(
      f'{url_for("strava_api.handle_code")}'
      '?code=some_code&scope=read,activity:read_all'
    )

    # Since the scope is accepted correctly, the user is redirected
    # to their strava account list. (Should it go to activity list instead?)
    self.assertEqual(rv.status_code, 302)
    self.assertEqual(rv.location, '/settings/strava')

    # Next, the external strava api responds to a POST request
    # from my app that includes the code that was previously
    # passed as a parameter on Strava's GET request to the callback url
    # (that strava interaction is mocked out here).
    # Then, the access token returned by strava is stored in the database.
    self.assertEqual(
      AdminUser().strava_accounts[0].access_token,
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


class TestManageAccounts(LoggedInFlaskTestCase):
  @patch('stravalib.model.Athlete.stats')
  @patch('stravalib.Client.get_athlete')
  @patch('stravalib.Client.refresh_access_token')
  def test_displays_account_info(self,  mock_refresh_access_token, mock_get_athlete, mock_stats):
    mock_refresh_access_token.return_value = MOCK_TOKEN
    mock_get_athlete.return_value = stravalib.model.Athlete(
      firstname='Aaron',
      lastname='Schroeder',
    )
    mock_stats.return_value = stravalib.model.AthleteStats(
      all_run_totals=stravalib.model.ActivityTotals(count=10)
    )

    db.session.add(StravaAccount(strava_id=1, expires_at=0))
    db.session.commit()
    self.client.get('/settings/strava')

    # TODO: Finish this test
  
  def test_displays_multiple_accounts(self):
    pass


class TestRevoke(AuthenticatedFlaskTestCase):
  @patch('stravalib.Client.get_athlete')
  @patch('stravalib.Client.refresh_access_token')
  def test_revoke(self, mock_refresh_access_token, mock_get_athlete):
    mock_get_athlete.return_value = stravalib.model.Athlete(
      firstname='Aaron', lastname='Schroeder')
    mock_refresh_access_token.return_value = MOCK_TOKEN

    strava_accts = AdminUser().strava_accounts
    self.assertEqual(len(strava_accts), 1)

    response = self.client.get(url_for('strava_api.revoke', id=strava_accts[0].strava_id))

    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, '/settings/strava')

    self.assertFalse(len(AdminUser().strava_accounts), 0)

  def test_revoke_on_strava(self):
    """The user revokes app access at https://www.strava.com/settings/apps
    
    Expected behavior: revoking access results in a webhook event
    """
    pass