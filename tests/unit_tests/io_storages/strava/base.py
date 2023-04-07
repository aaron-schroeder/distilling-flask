import os
import responses
import unittest

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaImportStorage
from distilling_flask.util.feature_flags import flag_set
from tests.unit_tests.base import FlaskTestCase


class StravaFlaskTestCase(FlaskTestCase):
  def setUp(self):
    self.mock_fresh_token = {'access_token': 'foo', 'refresh_token': 'bar', 
                             'expires_at': 1e10}
    self.api_mock = responses.RequestsMock()
    # self.api_mock.add_passthru('https://developers.strava.com/swagger')
    self.api_mock.start()  # pairs with .stop() and .reset()
    super().setUp()

  def tearDown(self):
    super().tearDown()
    self.api_mock.stop()
    self.api_mock.reset()

  def get_mock_token(self, expired=False):
    return {
      k: v if k != 'expires_at'
      else 1e10 * int(not bool(expired)) 
      for k, v in self.mock_fresh_token.items()
    }

  def create_strava_acct(self, token_expired=False):
    kwargs = dict(id=1, **self.get_mock_token(token_expired))
    strava_acct = (
      StravaImportStorage(**kwargs)
      if flag_set('ff_rename')
      else StravaImportStorage(**kwargs)
    )
    db.session.add(strava_acct)
    db.session.commit()
    return strava_acct


@unittest.skipIf(not os.getenv('TEST_NETWORK'),  # settings.SKIP_STRAVA_API,
                 'Skipping tests that require network connections')
class LiveStravaApiFlaskTestCase(FlaskTestCase):
  """
  NOTE: Some work is required before these tests will run correctly.
  
  This TestCase requires a database with valid StravaImportStorage
  connection. Since these tests involve real interactions with the Strava
  API, they need to present real oauth tokens, not fake ones.
  """
  clean_db = False

  def setUp(self):
    self._prev_db_url = os.getenv('TEST_DATABASE_URL')
    os.environ['TEST_DATABASE_URL'] = 'sqlite:///testdb.sqlite3'
    super().setUp()

  def tearDown(self):
    if self._prev_db_url:
      os.environ['TEST_DATABASE_URL'] = self._prev_db_url
      super().tearDown()
