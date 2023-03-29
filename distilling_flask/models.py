import datetime
import os
import sys

from flask import current_app
import pandas as pd
import sqlalchemy as sa

from distilling_flask import db
# from distilling_flask.io_storages.strava.models import StravaImportStorage
from distilling_flask.util import power, units


class AdminUser:
  id = 1

  def check_password(self, password):
    # password_correct = config.get('settings', 'password')
    password_correct = os.environ.get('PASSWORD', None)
    if password_correct:
      return password == password_correct

  # strava_accounts = db.relationship(
  #   'StravaImportStorage',
  #   backref='admin_user',
  #   lazy=True
  # )

  @property
  def strava_accounts(self):
    # return StravaImportStorage.query.all()
    return []  # HACK

  @property
  def settings(self):
    return UserSettings.query.get(self.id)

  def __repr__(self):
    return '<Admin User>'


class UserSettings(db.Model):
  id = db.Column(
    db.Integer,
    primary_key=True
  )

  cp_ms = db.Column(
    db.Float,
    nullable=False,
    server_default=sa.text(str(units.pace_to_speed('6:30')))
  )

  @property
  def ftp_ms(self):
    return self.cp_ms
  