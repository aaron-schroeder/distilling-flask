import os

import sqlalchemy as sa

from distilling_flask import db
from distilling_flask.util import units
from distilling_flask.util.feature_flags import flag_set


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
    # return db.session.scalars(db.select(StravaImportStorage)).all()
    # return StravaImportStorage.query.all()
    return []  # HACK to get around circular import for now

  @property
  def settings(self):
    if flag_set('ff_rename'):
      return UserSettings()
    else:
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
  