"""
Ref:
  https://www.obeythetestinggoat.com/book/chapter_unit_test_first_view.html
"""
import datetime
import os
import unittest

from flask_login import FlaskLoginClient

from distilling_flask import create_app, db
from distilling_flask.models import Activity, AdminUser, StravaAccount


BASEDIR = os.path.abspath(os.path.dirname(__file__))


class FlaskTestCase(unittest.TestCase):
  def setUp(self):
    """
    Refs:
      https://coddyschool.com/upload/Flask_Web_Development_Developing.pdf#page=221
      https://stackoverflow.com/questions/60111814/flask-distilling_flask-was-not-able-to-create-a-url-adapter-for-request
    """
    self.app = create_app(config_name='test')
    self.app.test_client_class = FlaskLoginClient
    self.test_request_context = self.app.test_request_context()
    self.test_request_context.push()
    self.app_context = self.app.app_context()
    self.app_context.push()
    self.client = self.app.test_client(use_cookies=True)
    db.create_all()

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    self.app_context.pop()
    self.test_request_context.pop()

  def create_activity(self, **kwargs):
    act = Activity(
      title=kwargs.get('title', 'title'),
      description=kwargs.get('description', 'description'),
      created=kwargs.get('created', datetime.datetime.utcnow()),
      recorded=kwargs.get('recorded', datetime.datetime.utcnow()),
      tz_local=kwargs.get('tz_local', 'UTC'),
      moving_time_s=kwargs.get('moving_time_s', 3600),
      elapsed_time_s=kwargs.get('elapsed_time_s', 3660),
      # Fields below here not required
      # strava_id=activity_data['id'],
      # distance_m=activity_data['distance'],
      # elevation_m=activity_data['total_elevation_gain'],
      ngp_ms=kwargs.pop('ngp_ms', None)
    )
    db.session.add(act)
    db.session.commit()

    return act


class LoggedInFlaskTestCase(FlaskTestCase):
  def setUp(self):
    super().setUp()
    self.client = self.app.test_client(user=AdminUser(), 
                                      #  use_cookies=True
                                       )


class AuthenticatedFlaskTestCase(LoggedInFlaskTestCase):
  def setUp(self):
    super().setUp()
    self.strava_acct = StravaAccount(strava_id=1, expires_at=0)
    db.session.add(self.strava_acct)
    db.session.commit()