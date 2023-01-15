import datetime
from functools import cached_property
from importlib import import_module
import os
import sys

from flask import current_app
from flask_login import UserMixin
import pytz
from stravalib.exc import RateLimitExceeded

from application import db, login
from application.util import units


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


class Activity(db.Model):
  """Data model for activities."""

  # Only need to define this if I want to override default lowercase
  # eg __tablename__ = 'activity' by default
  # __tablename__ = 'activities'

  id = db.Column(
    db.Integer,
    primary_key=True
  )

  title = db.Column(
    db.String(255),
    unique=False,
    nullable=True,  # Why force it?
  )

  description = db.Column(
    db.Text,
    unique=False,
    nullable=True,
  )

  created = db.Column(
    db.DateTime,
    unique=False,
    nullable=False
  )

  recorded = db.Column(
    db.DateTime,
    unique=False,
    nullable=False
  )

  tz_local = db.Column(
    db.String(40),  # I checked and 32 is max length
    unique=False,
    nullable=False,
    default='UTC',
  )
  
  # Doesn't necessarily exist, but must be unique if it does.
  strava_id = db.Column(
    db.BigInteger,
    unique=True,
    nullable=True,
  )

  # CAN link to strava acct, but does not have to.
  strava_acct_id = db.Column(
    db.Integer,
    db.ForeignKey('strava_account.strava_id')
  )

  # Maybe (strava, file upload, etc)
  # String
  # data_source = ...

  # Nullable because not every activity has latlons, so getting vals 
  # might not be possible.
  distance_m = db.Column(
    db.Float,
    unique=False,
    nullable=True,
  )

  # Figured rounding to the nearest meter isn't a loss of precision.
  # Nullable because not every activity has latlons, so getting vals 
  # might not be possible.
  elevation_m = db.Column(
    db.Integer,
    unique=False,
    nullable=True,
  )

  # I think this should be required. All activities should have time as
  # a bare minimum.
  elapsed_time_s = db.Column(
    db.Integer,
    unique=False,
    nullable=False,
  )

  # I think this should be required. Can be the same as elapsed_time_s
  # in a pinch.
  moving_time_s = db.Column(
    db.Integer,
    unique=False,
    nullable=False,
  )

  ngp_ms = db.Column(
    db.Float,
    unique=False,
    nullable=True
  )

  @property
  def intensity_factor(self):
    if self.ngp_ms:
      # return self.ngp_ms / AdminUser().get_ftp_ms(self.recorded)
      return self.ngp_ms / units.pace_to_speed('6:30')

  @property
  def tss(self):
    if self.intensity_factor:
      return 100.0 * (self.elapsed_time_s / 3600) * self.intensity_factor ** 2

  @property
  def relative_url(self):
    return f'/saved/{self.id}'

  @classmethod
  def find_overlap_ids(cls, datetime_st, datetime_ed):
    return [
      activity.id
      for activity in cls.query.all()
      if (
        datetime_st < pytz.utc.localize(activity.recorded)
          + datetime.timedelta(seconds=activity.elapsed_time_s)
        and pytz.utc.localize(activity.recorded) < datetime_ed
      )
    ]

  def __repr__(self):
      return '<Activity {}>'.format(self.id)


class AdminUser(UserMixin):
  id = 1
  # strava_accounts = db.relationship(
  #   'StravaAccount',
  #   backref='admin_user',
  #   lazy=True
  # )

  def check_password(self, password):
    # password_correct = config.get('settings', 'password')
    password_correct = os.environ.get('PASSWORD', None)
    if password_correct:
      return password == password_correct

  @property
  def strava_accounts(self):
    return StravaAccount.query.all()

  def __repr__(self):
    return '<Admin User>'


@login.user_loader
def load_user(id):
  return AdminUser()


def cached_import(module_path, class_name):
  """
  based on `django.utils.module_loading.import_string`
  """

  # Check whether module is loaded and fully initialized.
  if not (
    (module := sys.modules.get(module_path))
    and (spec := getattr(module, "__spec__", None))
    and getattr(spec, "_initializing", False) is False
  ):
    module = import_module(module_path)
  return getattr(module, class_name)


def import_string(dotted_path):
  """
  Import a dotted module path and return the attribute/class designated by the
  last name in the path. Raise ImportError if the import failed.

  based on `django.utils.module_loading.import_string`
  """
  try:
    module_path, class_name = dotted_path.rsplit(".", 1)
  except ValueError as err:
    raise ImportError("%s doesn't look like a module path" % dotted_path) from err

  try:
    return cached_import(module_path, class_name)
  except AttributeError as err:
    raise ImportError(
      'Module "%s" does not define a "%s" attribute/class'
      % (module_path, class_name)
    ) from err


class StravaAccount(db.Model):
  # admin_user_id = db.Column(
  #   db.Integer,
  #   db.ForeignKey('admin_user.id'),
  #   nullable=False
  # )
  # admin_user_id = 1
  strava_id = db.Column(
    db.Integer,
    primary_key=True
  )
  access_token = db.Column(db.String())
  refresh_token = db.Column(db.String())
  expires_at = db.Column(db.Integer)
  # email = db.Column(db.String)
  # token = db.Column(db.PickleType)
  activities = db.relationship('Activity', backref='strava_acct', lazy='dynamic')

  # @property
  def get_token(self):

    if datetime.datetime.utcnow() < datetime.datetime.utcfromtimestamp(self.expires_at):
      return dict(
        access_token=self.access_token,
        refresh_token=self.refresh_token,
        expires_at=self.expires_at,
      )

    print('refreshing expired token')
    token = self.get_client().refresh_access_token(
      client_id=CLIENT_ID,
      client_secret=CLIENT_SECRET,
      refresh_token=self.refresh_token
    )

    self.access_token = token['access_token']
    self.refresh_token = token['refresh_token']
    self.expires_at = token['expires_at']
    db.session.commit()

    return token

  @property
  def has_authorized(self):
    return self.access_token is not None

  @property
  def client(self):
    token = self.get_token()
    return self.get_client(access_token=token['access_token'])

  @staticmethod
  def get_client(backend=None, access_token=None):
    """Load a strava connection backend and return an instance of it.
    If backend is None (default), use `config.STRAVA_API_BACKEND`, or
    finally default to stravalib.
    """
    backend = backend or current_app.config.get('STRAVA_API_BACKEND')
    klass = import_string(backend or 'stravalib.Client')
    return klass(access_token=access_token)

  @cached_property
  def athlete(self):
    try:
      _athlete = self.client.get_athlete()
    except RateLimitExceeded:
      # HACK
      class AthUhLete(object):
        def __init__(zelf, *args, **kwargs):
          for attr_nm, attr in kwargs.items():
            setattr(zelf, attr_nm, attr)
      
      _athlete = AthUhLete(
        profile=None,
        firstname='Rate',
        lastname='Limit',
        run_count=None,
        follower_count=None,
        email=None,
      )
    
    return _athlete

  @property
  def profile_picture_url(self):
    return self.athlete.profile

  @property
  def firstname(self):
    return self.athlete.firstname

  @property
  def lastname(self):
    return self.athlete.lastname

  @property
  def run_count(self):
    return self.athlete.stats.all_run_totals.count

  @property
  def follower_count(self):
    return self.athlete.follower_count

  @property
  def email(self):
    return self.athlete.email

  @property
  def url(self):
    return f'https://www.strava.com/athletes/{self.strava_id}'