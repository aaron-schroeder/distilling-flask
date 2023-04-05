import datetime

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaImportStorage
from distilling_flask.util.feature_flags import flag_set
from tests.unit_tests.base import FlaskTestCase


class AuthenticatedFlaskTestCase(FlaskTestCase):
  def setUp(self):
    super().setUp()
    self.strava_acct = (
      StravaImportStorage(id=1, expires_at=0) 
      if flag_set('ff_rename')
      else StravaImportStorage(strava_id=1, expires_at=0)
    )
    db.session.add(self.strava_acct)
    db.session.commit()
