import datetime
import enum
import json
import os

import stravalib

from distilling_flask import db
from distilling_flask.io_storages.models import ImportStorage, ImportStorageLink


ActivityTypeEnum = enum.Enum('ActivityTypeEnum', 
  {f.upper(): f for f in stravalib.model.Activity.TYPES})


class StravaStorageMixin:
  access_token = db.Column(db.String())
  refresh_token = db.Column(db.String())
  expires_at = db.Column(db.Integer)
  activity_type = db.Column(
    db.Enum(ActivityTypeEnum), 
    default=ActivityTypeEnum.RUN,
    nullable=False
  )

  def get_client(
    self,
    access_token=None,
    client_id=None,
    client_secret=None,
    validate_connection=False
  ):
    access_token = access_token or os.environ.get('STRAVA_ACCESS_TOKEN')
    client_id = client_id or os.environ.get('STRAVA_CLIENT_ID')
    client_secret = client_id or os.environ.get('STRAVA_CLIENT_SECRET')
    
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
  def iterkeys(self):
    client = self.get_client()
    for activity in client.get_activities():
      key = activity.id
      if self.activity_type and activity.type != self.activity_type:
        # logger.debug(key + ' is skipped because it is not a ' + activity_type)
        continue
      yield key

  def scan_and_create_links(self):
    return self._scan_and_create_links(StravaImportStorageLink)

  def get_data(self, key):
    """
    `key` refers to Strava activity ID here.
    """
    client = self.get_client()
    
    activity_summary = client.get_activity(key)
    activity_streams = client.get_activity_streams(key, types=(
      'time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
      'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth'
    ))

    return {
      'summary': activity_summary.to_dict(),
      'streams': activity_streams.to_dict(),
    }


class StravaImportStorageLink(ImportStorageLink):
  # storage = models.ForeignKey(StravaImportStorage, on_delete=models.CASCADE, related_name='links')
  pass