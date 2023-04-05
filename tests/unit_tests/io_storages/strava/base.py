import datetime

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaImportStorage
from tests.unit_tests.base import FlaskTestCase


class AuthenticatedFlaskTestCase(FlaskTestCase):
  def setUp(self):
    super().setUp()
    self.strava_acct = StravaImportStorage(strava_id=1, expires_at=0)
    db.session.add(self.strava_acct)
    db.session.commit()
    