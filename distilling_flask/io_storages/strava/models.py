import datetime
import enum
from functools import cached_property
import json
import os

from dateutil import tz
import pandas as pd
import pytz
import stravalib
from stravalib.exc import RateLimitExceeded

from distilling_flask import db
from distilling_flask.models import AdminUser
from distilling_flask.io_storages.models import (
  ImportStorage,
  ImportStorageEntity
)
from distilling_flask.util import power


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


ActivityTypeEnum = enum.Enum('ActivityTypeEnum', 
  {f.upper(): f for f in stravalib.model.Activity.TYPES})


class StravaStorageMixin:
  access_token = db.Column(db.String())
  refresh_token = db.Column(db.String())
  expires_at = db.Column(db.Integer)
  # activity_type = db.Column(
  #   db.Enum(ActivityTypeEnum), 
  #   default=ActivityTypeEnum.RUN,
  #   nullable=False
  # )

  def get_client(
    self,
    access_token=None,
    client_id=None,
    client_secret=None,
    validate_connection=False
  ):
    access_token = access_token or os.environ.get('STRAVA_ACCESS_TOKEN')
    client_id = client_id or CLIENT_ID
    client_secret = client_secret or CLIENT_SECRET
    
    client = stravalib.Client()

    if access_token:
      client.access_token = access_token
    elif client_id and client_secret:
      if not self.token_expired:
        client.access_token = self.access_token
      else:
        try:
          token = client.refresh_access_token(
            client_id,
            client_secret,
            self.refresh_token
          )
        except Exception as e:
          print('ahhhhhhhhhhhhhhhhhhhhhhhhhhHHHHHHHH')
          pass
        else:
          self.access_token = token['access_token']
          self.refresh_token = token['refresh_token']
          self.expires_at = token['expires_at']
          db.session.commit()

    if validate_connection:
      self.validate_connection(client)

    return client
  
  def validate_connection(self, client=None):
    # logger.debug('validate_connection')
    if client is None:
      client = self.get_client()

    # logger.debug(f'Test connection to bucket {self.bucket} with prefix {self.prefix}')
    client.get_activities(limit=5)

  @property
  def token_expired(self):
    return datetime.datetime.utcnow() < datetime.datetime.utcfromtimestamp(self.expires_at)
  

class StravaImportStorage(StravaStorageMixin, ImportStorage):

  __tablename__ = 'strava_account'

  entities = db.relationship('StravaApiActivity', backref='import_storage', lazy='dynamic')

  # def iterkeys(self):
  #   client = self.get_client()
  #   for activity in client.get_activities():
  #     yield activity.id
  #     # if self.activity_type and activity.type != self.activity_type:
  #     #   # logger.debug(
  #     #   print(key + ' is skipped because it is not a ' + activity_type)
  #     #   continue

  # def scan_and_create_entities(self):
  #   return self._scan_and_create_entities(StravaApiActivity)

  # def get_data(self, key):
  #   """
  #   `key` refers to Strava activity ID here.
  #   """
  #   client = self.get_client()
    
  #   activity_summary = client.get_activity(key)
  #   activity_streams = client.get_activity_streams(key, types=(
  #     'time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
  #     'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth'
  #   ))

  #   return {
  #     'summary': activity_summary.to_dict(),
  #     'streams': activity_streams.to_dict(),
  #   }


  # def get_token(self):

  #   if datetime.datetime.utcnow() < datetime.datetime.utcfromtimestamp(self.expires_at):
  #     return dict(
  #       access_token=self.access_token,
  #       refresh_token=self.refresh_token,
  #       expires_at=self.expires_at,
  #     )

  #   print('refreshing expired token')
  #   token = self.get_client().refresh_access_token(
  #     client_id=CLIENT_ID,
  #     client_secret=CLIENT_SECRET,
  #     refresh_token=self.refresh_token
  #   )

  #   self.access_token = token['access_token']
  #   self.refresh_token = token['refresh_token']
  #   self.expires_at = token['expires_at']
  #   db.session.commit()

  #   return token

  @property
  def has_authorized(self):
    return self.access_token is not None

  # @property
  # def client(self):
  #   token = self.get_token()
  #   return self.get_client(access_token=token['access_token'])

  # @staticmethod
  # def get_client(backend=None, access_token=None):
  #   """Load a strava connection backend and return an instance of it.
  #   If backend is None (default), use `config.STRAVALIB_CLIENT`, or
  #   finally default to stravalib.
  #   """
  #   backend = backend or current_app.config.get('STRAVALIB_CLIENT')
  #   klass = import_string(backend or 'stravalib.Client')
  #   for cfg_name, cfg_val in current_app.config.items():
  #     if (
  #       cfg_name.startswith('MOCK_STRAVALIB_') 
  #       and current_app.config.get(cfg_name)
  #     ):
  #       setattr(
  #         klass,
  #         cfg_name.split('MOCK_STRAVALIB')[1].lower(),
  #         cfg_val
  #       )
  #   return klass(access_token=access_token)

  # @cached_property
  # def athlete(self):
  #   try:
  #     _athlete = self.client.get_athlete()
  #   except RateLimitExceeded:
  #     from distilling_flask.util.mock_stravalib import DummyClass
      
  #     _athlete = DummyClass(
  #       profile=None,
  #       firstname='Rate',
  #       lastname='Limit',
  #       follower_count=None,
  #       email=None,
  #       city=None,
  #       state=None,
  #       country=None,
  #       stats=DummyClass(
  #         all_run_totals=DummyClass(count=1)
  #       )
  #     )
    
  #   return _athlete

  # @property
  # def profile_picture_url(self):
  #   return self.athlete.profile

  # @property
  # def firstname(self):
  #   return self.athlete.firstname

  # @property
  # def lastname(self):
  #   return self.athlete.lastname

  # @property
  # def run_count(self):
  #   return self.athlete.stats.all_run_totals.count

  # @property
  # def follower_count(self):
  #   return self.athlete.follower_count

  # @property
  # def email(self):
  #   return self.athlete.email

  @property
  def url(self):
    return f'https://www.strava.com/athletes/{self.strava_id}'


class StravaApiActivity(ImportStorageEntity):
  __tablename__ = 'activity'
  __abstract__ = False

  # summary = db.Column(db.BLOB)
  # streams = db.Column(db.BLOB)

  # import_storage_id = db.Column(
  strava_acct_id = db.Column(
    db.Integer,
    # TODO: How to make this required?
    db.ForeignKey('strava_account.strava_id')
    # db.ForeignKey('strava_import_storage.strava_id')
    # db.ForeignKey('strava_import_storage.id')
  )

  # strava_id = db.Column(
  #   db.BigInteger,
  #   unique=True,
  #   nullable=True,
  # )

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
      return power.intensity_factor(self.ngp_ms, AdminUser().settings.ftp_ms)

  @property
  def tss(self):
    if self.ngp_ms:
      return power.training_stress_score(
        self.ngp_ms, AdminUser().settings.ftp_ms, self.elapsed_time_s)

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

  @classmethod
  def load_table_as_df(cls, fields=None):

    fields = fields or ['recorded', 'title', 'elapsed_time_s',
      'moving_time_s', 'elevation_m', 'distance_m', 'id', 'description',
      'strava_acct_id']

    # see also: pd.read_sql_query()
    df = pd.read_sql_table(
      cls.__tablename__,
      db.engine
    )

    if not len(df):
      return df

    df = df.sort_values(by='recorded', axis=0)

    # For now, convert to my tz - suggests setting TZ by user,
    # not by activity.
    df['recorded'] = df['recorded'].dt.tz_localize(tz.tzutc()).dt.tz_convert(tz.gettz('America/Denver'))

    return df

  def __repr__(self):
      return '<Activity {}>'.format(self.id)
