import json

from flask import url_for
import responses

from distilling_flask import db
from distilling_flask.models import AdminUser
from distilling_flask.io_storages.strava.models import StravaImportStorage
from distilling_flask.util.feature_flags import flag_set
from tests.unit_tests.base import FlaskTestCase
from tests.unit_tests.io_storages.strava.base import StravaFlaskTestCase


# class TestAuthorize(FlaskTestCase):
class TestAuthorize(StravaFlaskTestCase):
  def test_strava_oauth_authorize(self):
    rv = self.client.get(url_for('strava_api.authorize'))
    
    # response should be a redirect
    self.assertEqual(rv.status_code, 302)
    # should redirect to strava's authorization endpoint
    self.assertEqual(rv.location.split('?')[0],
                     'https://www.strava.com/oauth/authorize')

    # TODO: figure out if more testing is called for


class TestHandleCode(StravaFlaskTestCase):
  def test_strava_oauth_callback(self):
    with open('tests/unit_tests/sample_data/exchange_code_for_token.json', 'r') as f:
      resp_json = json.load(f)
    self.api_mock.add(
      responses.POST,
      'https://www.strava.com/oauth/token',
      json=resp_json,
      status=200)
    rv = self.client.get(
      f'{url_for("strava_api.handle_code")}'
      # f'{url_for("strava.handle_code")}'
      '?code=some_code&scope=read,activity:read_all')

    # Since the scope is accepted correctly, the user is redirected
    # to their strava account list. (Should it go to activity list instead?)
    self.assertEqual(rv.status_code, 302)
    self.assertEqual(rv.location, '/settings/strava')

    # Next, the external strava api responds to a POST request
    # from my app that includes the code that was previously
    # passed as a parameter on Strava's GET request to the callback url
    # (that strava interaction is mocked out here).
    # Then, the access token returned by strava is stored in the database.
    acct = db.session.scalars(db.select(StravaImportStorage)).first()  \
      if flag_set('ff_rename') else AdminUser().strava_accounts[0]
    self.assertEqual(acct.access_token, resp_json['access_token'])

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
    self.assertIn('Please accept the permission', rv.get_data(as_text=True))

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


class TestRevoke(StravaFlaskTestCase):
  def test_revoke(self):
    strava_acct = self.create_strava_acct()

    response = self.client.get(url_for('strava_api.revoke',
      id=strava_acct.id if flag_set('ff_rename') 
        else strava_acct.strava_id
      ))
    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, '/settings/strava')

    self.assertEqual(
      len(db.session.scalars(db.select(StravaImportStorage)).all()
          if flag_set('ff_rename')
          else AdminUser().strava_accounts), 
      0)

  def test_revoke_on_strava(self):
    """The user revokes app access at https://www.strava.com/settings/apps
    
    Expected behavior: revoking access results in a webhook event
    """
    pass