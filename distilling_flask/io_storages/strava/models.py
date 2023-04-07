import datetime
import json
import os
import zlib

from celery import group
import dateutil
import pandas as pd
import pytz
from scipy.interpolate import interp1d
from stravalib.exc import RateLimitExceeded

from distilling_flask import db, celery
from distilling_flask.models import AdminUser
from distilling_flask.io_storages.base_models import (
  ImportStorage,
  ImportStorageEntity
)
from distilling_flask.io_storages.strava import util
from distilling_flask.util import power, readers
from distilling_flask.util.dataframe import calc_power
from distilling_flask.util.feature_flags import flag_set


class StravaStorageMixin:
  access_token = db.Column(db.String())
  refresh_token = db.Column(db.String())
  expires_at = db.Column(db.Integer)

  def get_client(
    self,
    # access_token=None,
    client_id=None,
    client_secret=None,
    validate_connection=False
  ):
    client_id = client_id or os.getenv('STRAVA_CLIENT_ID')
    client_secret = client_secret or os.getenv('STRAVA_CLIENT_SECRET')
      # access_token = access_token or os.getenv('STRAVA_ACCESS_TOKEN')
    if self.token_expired:
      auth_client = util.StravaOauthClient(client_id, client_secret)
      resp = auth_client.post('/token', refresh_token=self.refresh_token,
                              grant_type='refresh_token')
      token = resp.json()
      # token = client.refresh_access_token(self.refresh_token)
      self.access_token = token['access_token']
      self.refresh_token = token['refresh_token']
      self.expires_at = token['expires_at']
      db.session.commit()
    client = util.StravaApiClient(client_id, client_secret, self.access_token)
    if validate_connection:
      self.validate_connection(client)
    return client
  
  def validate_connection(self, client=None):
    # logger.debug(
    print('validate_connection')
    if client is None:
      client = self.get_client()

    # TODO GH48: Handle rate limiting here and wherever else it occurs.
    # logger.debug(f'Test connection to bucket {self.bucket} with prefix {self.prefix}')
    _ = client.get('/athlete')

  @property
  def token_expired(self):
    return datetime.datetime.utcnow() > datetime.datetime.utcfromtimestamp(self.expires_at)


class StravaImportStorage(StravaStorageMixin, ImportStorage):
  __tablename__ = 'strava_account'

  entities = db.relationship(
    'StravaApiActivity',
    backref='import_storage' if flag_set('ff_rename') else 'strava_acct', 
    lazy='dynamic')

  @property
  def activities(self):
    print('StravaApiActivity: `activities` is deprecated in favor of `entities`.')
    return self.entities

  def iterkeys(self):
    client = self.get_client()
    page = 1
    while True:
      # TODO GH48
      resp = client.get('/athlete/activities', page=page, per_page=200)

      # TODO (GH??): Bring the following functionality into the package.
      # Response pickling lets any user record sample responses for 
      # their own strava interactions:
      # import pickle
      # with open('resp.pickle', 'wb') as f:
      #   pickle.dump(resp, f)

      if len(activity_list := resp.json()) and isinstance(activity_list, list):
        for activity_summary in activity_list:
          yield activity_summary['id']
        page += 1
      else:
        break

  def scan_and_create_entities(self):
    return self._scan_and_create_entities(StravaApiActivity)

  def get_data(self, key):
    """
    `key` refers to Strava activity ID here.
    """
    data = dict(
      created=datetime.datetime.utcnow(),  
      # # ngp_ms=ngp_scalar,
    )
    data['key' if flag_set('ff_rename') else 'strava_id'] = key  # summary_data['id'] too
    
    client = self.get_client()
    # TODO GH48
    summary_resp = client.get(f'/activities/{key}', include_all_efforts=True)
    summary_data = summary_resp.json()
    if flag_set('ff_rename'):
      # activity_summary = client.get_activity(key)
      # summary_data = activity_summary.to_dict()
      # data['summary'] = json.dumps(summary_data).encode('utf-8')
      data['summary_compressed'] = zlib.compress(json.dumps(summary_data).encode('utf-8'))

      # TODO GH48
      stream_resp = client.get(
        f'/activities/{key}/streams/time,latlng,distance,altitude,'
        f'velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth')
      stream_data = stream_resp.json()
      # data['streams'] = json.dumps(stream_data).encode('utf-8')
      data['streams_compressed'] = zlib.compress(json.dumps(stream_data).encode('utf-8'))
    else:
      # activity_streams = client.get_activity_streams(key, types=(
      #   'time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
      #   'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth'
      # ))
      # if activity_streams:
      #   df = readers.from_strava_streams(activity_streams)
      #   calc_power(df)
      #   ngp_scalar = None
      #   if 'NGP' in df.columns:
      #     # Resample the NGP stream at 1 sec intervals
      #     # TODO: Figure out how/where to make this repeatable.
      #     # 1sec even samples make the math so much easier.
      #     interp_fn = interp1d(df['time'], df['NGP'], kind='linear')
      #     ngp_1sec = interp_fn([i for i in range(df['time'].max())])

      #     # Apply a 30-sec rolling average.
      #     window = 30
      #     ngp_rolling = pd.Series(ngp_1sec).rolling(window).mean()          
      #     ngp_scalar = power.lactate_norm(ngp_rolling[29:])
      #   elif 'speed' in df.columns:
      #     # TODO: Add capabilities for flat-ground TSS.
      #     pass
      data.update(dict(
        title=summary_data['name'], # or `activity_summary.name`
        description=summary_data['description'],
        recorded=dateutil.parser.isoparse(summary_data['start_date']),
        moving_time_s=summary_data['moving_time'],
        elapsed_time_s=summary_data['elapsed_time'],
        # Fields below here not required
        tz_local=summary_data['timezone'],
        distance_m=summary_data['distance'],
        elevation_m=summary_data['total_elevation_gain'],
      ))

    # Debug
    # for k, v in data.items():
    #   if k == 'summary':
    #     print(f'{k}: {{big ol doc}}')
    #   else:
    #     print(f'{k}:{v}')
    
    return data

  @property
  def has_authorized(self):
    return self.access_token is not None

  @property
  def url(self):
    return f'https://www.strava.com/athletes/{self.id if flag_set("ff_rename") else self.strava_id}'


class StravaApiActivity(ImportStorageEntity):
  __tablename__ = 'activity'
  __abstract__ = False

  if flag_set('ff_rename'):
    import_storage_id = db.Column(
      # db.Integer, db.ForeignKey('strava_import_storage.id'))
      db.Integer, db.ForeignKey('strava_account.id'))
    
    @property
    def strava_acct_id(self):
      print(f'Use of `strava_acct_id` for StravaApiActivity is '
          f'deprecated in favor of `import_storage_id`.')
      return self.import_storage_id
  else:
    strava_acct_id = db.Column(
      db.Integer, db.ForeignKey('strava_account.id'))

  title = property(lambda self: self.summary.get('name'))  \
          if flag_set('ff_rename')  \
          else db.Column(
            db.String(255),
            unique=False,
            nullable=True,
          )

  description = property(lambda self: self.summary['description'])  \
                if flag_set('ff_rename')  \
                else db.Column(
                  db.Text,
                  unique=False,
                  nullable=True,
                )

  recorded = property(lambda self: dateutil.parser.isoparse(self.summary['start_date']))  \
             if flag_set('ff_rename')  \
             else db.Column(
               db.DateTime,
               unique=False,
               nullable=False
             )

  tz_local = property(lambda self: self.summary['timezone'])  \
          if flag_set('ff_rename')  \
          else db.Column(
            db.String(40),
            unique=False,
            nullable=False,
            default='UTC',
          )

  # Nullable because not every activity has latlons, so getting vals 
  # might not be possible.
  distance_m = property(lambda self: float(self.summary['distance']))  \
               if flag_set('ff_rename')  \
               else db.Column(
                 db.Float,
                 unique=False,
                 nullable=True,
               )

  # Figured rounding to the nearest meter isn't a loss of precision.
  # Nullable because not every activity has latlons, so getting vals 
  # might not be possible.
  elevation_m = property(lambda self: int(self.summary['total_elevation_gain']))  \
          if flag_set('ff_rename')  \
          else db.Column(
      db.Integer,
      unique=False,
      nullable=True,
    )

  elapsed_time_s = property(lambda self: int(self.summary['elapsed_time']))  \
          if flag_set('ff_rename')  \
          else db.Column(
      db.Integer,
      unique=False,
      nullable=False,
    )

  moving_time_s = property(lambda self: int(self.summary['moving_time']))  \
          if flag_set('ff_rename')  \
          else db.Column(
      db.Integer,
      unique=False,
      nullable=False,
    )

  ngp_ms = db.Column(
    db.Float,
    unique=False,
    nullable=True
  )

  if flag_set('ff_rename'):
    summary_compressed = db.Column(db.BLOB)
    streams_compressed = db.Column(db.BLOB)

    @property
    def summary(self):
      if not getattr(self, '_summary', False):
        self._summary = json.loads(zlib.decompress(self.summary_compressed))
      return self._summary
    
    @property
    def streams(self):
      if not getattr(self, '_streams', False):
        self._streams = json.loads(zlib.decompress(self.streams_compressed))
      return self._streams
  
    # # NOTE: This is just a first stab at backwards-compatibility with db schema.
    # summary_compressed = db.Column(db.BLOB)   \
    #                     if flag_set('ff_rename')  \
    #                     else None 
    
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
  def load_table_as_df(cls):
    if flag_set('ff_rename'):
      df = pd.DataFrame([
        {
          'id': activity.id,
          'created': activity.created,
          'title': activity.title,
          'description': activity.description,
          'recorded': activity.recorded,
          'tz_local': activity.tz_local,
          'distance_m': activity.distance_m,
          'elevation_m': activity.elevation_m,
          'elapsed_time_s': activity.elapsed_time_s,
          'moving_time_s': activity.moving_time_s,
          'ngp_ms': activity.ngp_ms,
          # 'intensity_factor': activity.intensity_factor,
          # 'tss': activity.tss,
          'import_storage_id': activity.import_storage_id, 
        }
        for activity in db.session.scalars(db.select(cls)).all()
      ])
    else:
      # see also: pd.read_sql_query()
      df = pd.read_sql_table(
        cls.__tablename__,
        db.engine
      )
      df['recorded'] = df['recorded'].dt.tz_localize(dateutil.tz.tzutc())

    if not len(df):
      return df

    # Standard practices seem to suggest setting TZ by user, not by activity.
    # For now, convert to my tz.
    if 'recorded' in df.columns:
      df['recorded'] = df['recorded'].dt.tz_convert(dateutil.tz.gettz('America/Denver'))
      df = df.sort_values(by='recorded', axis=0)

    return df

  def __repr__(self):
      return '<Activity {}>'.format(self.id)

if flag_set('ff_rename'):

  @celery.task(bind=True)
  def async_save_strava_activity(self, storage_id, entity_id, handle_overlap='existing'):
    storage = db.session.get(StravaImportStorage, storage_id)
    try:
      data = storage.get_data(entity_id)
    except RateLimitExceeded:
      # This generates retries in 3, 9, and 27 minutes.
      self.retry(countdown=180 * 3 ** self.request.retries,
                 max_retries=3)
    db.session.add(StravaApiActivity(**data))
    db.session.commit()


  @celery.task(bind=True)
  def sync_strava_background(self, storage_id, handle_overlap='existing'):
    """Master task that spawns a task for each activity."""
    storage = db.session.get(StravaImportStorage, storage_id)

    # for key in storage.iterkeys():
    #   if StravaApiActivity.exists(key, storage):
    #     pass

    # saved_strava_activity_ids = [saved_activity.key 
    #                              for saved_activity in storage.entities.all()]
    try:
      activity_ids = list(k for k in storage.iterkeys()
                          if not StravaApiActivity.exists(k, storage))
    except RateLimitExceeded:
      # This generates retries in 1, 3, and 9 minutes.
      self.retry(countdown=60 * 3 ** self.request.retries,
                 max_retries=3)

    client = storage.get_client()
    num_15_max = util.est_15_min_rate(client)
    for chunk_index, i in enumerate(range(0, len(activity_ids), num_15_max)):
      activity_ids_15_min = activity_ids[i:i + num_15_max]
      group_15_min = group(
        async_save_strava_activity.s(
          storage_id,
          strava_activity_id,
          handle_overlap=handle_overlap
        )
        for strava_activity_id in activity_ids_15_min
      )
      group_15_min.apply_async(countdown=15 * 60 * chunk_index)

else:
  from distilling_flask.io_storages.strava.models import StravaImportStorage, StravaApiActivity

  @celery.task(bind=True)
  def async_save_strava_activity(self, account_id, activity_id, handle_overlap='existing'):

    strava_acct = StravaImportStorage.query.get(account_id)
    client = strava_acct.get_client()
    
    try:
      activity = client.get_activity(activity_id)
    except RateLimitExceeded:
      # This generates retries in 3, 9, and 27 minutes.
      self.retry(
        countdown=180 * 3 ** self.request.retries,
        max_retries=3,
      )

    if activity.type not in ('Run', 'Walk', 'Hike'):
      print(f"Throwing out a {activity_data['type']}")
      return

    # check for saved activity with identical strava id;
    # if it exists, skip saving the new activity
    if StravaApiActivity.query.filter_by(strava_id=activity.id).count():
      print(f'Saved activity with strava id {activity.id} already exists...skipping.')
      return

    # check for overlapping saved activities and handle accordingly
    overlap_ids = StravaApiActivity.find_overlap_ids(
      activity.start_date,
      activity.start_date + activity.elapsed_time
    )
    if len(overlap_ids):
      print('Overlapping existing activities detected.')
      if handle_overlap == 'existing':
        print('Keeping existing activities; not saving incoming strava activity.')
        return
      elif handle_overlap == 'both':
        print('Keeping existing activities AND saving incoming strava activity.')
        pass
      elif handle_overlap == 'incoming':
        print('Deleting existing activities and saving incoming strava activity.')
        for saved_activity_id in overlap_ids:
          db.session.delete(StravaApiActivity.query.get(saved_activity_id))
          db.session.commit()
    else:
      print('No overlaps detected')
      pass
    
    try:
      activity_streams = client.get_activity_streams(
        activity_id,
        types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
            'heartrate', 'cadence', 'watts', 'temp', 'moving',
            'grade_smooth']
      )
    except RateLimitExceeded:
      self.retry(
        countdown=180 * 3 ** self.request.retries,
        max_retries=3,
      )

    if activity_streams:
      df = readers.from_strava_streams(activity_streams)
      calc_power(df)
      ngp_scalar = None
      if 'NGP' in df.columns:
        # Resample the NGP stream at 1 sec intervals
        # TODO: Figure out how/where to make this repeatable.
        # 1sec even samples make the math so much easier.
        interp_fn = interp1d(df['time'], df['NGP'], kind='linear')
        ngp_1sec = interp_fn([i for i in range(df['time'].max())])

        # Apply a 30-sec rolling average.
        window = 30
        ngp_rolling = pd.Series(ngp_1sec).rolling(window).mean()          
        ngp_scalar = power.lactate_norm(ngp_rolling[29:])
      elif 'speed' in df.columns:
        # TODO: Add capabilities for flat-ground TSS.
        pass

    activity_data = activity.to_dict()

    db.session.add(StravaApiActivity(
      title=activity_data['name'],
      description=activity_data['description'],
      created=datetime.datetime.utcnow(),  
      recorded=dateutil.parser.isoparse(activity_data['start_date']),
      tz_local=activity_data['timezone'],
      moving_time_s=activity_data['moving_time'],
      elapsed_time_s=activity_data['elapsed_time'],
      # Fields below here not required
      strava_id=activity_data['id'],
      strava_acct_id=strava_acct.strava_id,
      distance_m=activity_data['distance'],
      elevation_m=activity_data['total_elevation_gain'],
      ngp_ms=ngp_scalar,
      # intensity_factor=intensity_factor,
      # tss=tss,
    ))
    db.session.commit()


@celery.task(bind=True)
def async_save_all_strava_activities(self, strava_account_id, handle_overlap='existing'):
  """Master task that (hopefully) spawns a task for each activity."""
  strava_acct = StravaImportStorage.query.get(strava_account_id)
  saved_strava_activity_ids = [saved_activity.strava_id for saved_activity in strava_acct.activities.all()]
  client = strava_acct.get_client()

  try:
    # activity_ids = [activity.id for activity in client.get_activities()]
    # activity_dicts = [activity.to_dict() for activity in client.get_activities()]
    activity_ids = [
      activity.id 
      for activity in client.get_activities()
      if (
        activity.type in ('Run', 'Walk', 'Hike')
        and activity.id not in saved_strava_activity_ids
      )
    ]

  except RateLimitExceeded:
    # This generates retries in 1, 3, and 9 minutes.
    self.retry(
      countdown=60 * 3 ** self.request.retries,
      max_retries=3,
    )

  num_15_max = util.est_15_min_rate(client)
  for chunk_index, i in enumerate(range(0, len(activity_ids), num_15_max)):
    activity_ids_15_min = activity_ids[i:i + num_15_max]
    group_15_min = group(
      async_save_strava_activity.s(
        strava_account_id,
        strava_activity_id,
        handle_overlap=handle_overlap
      )
      for strava_activity_id in activity_ids_15_min
    )
    group_15_min.apply_async(countdown=15 * 60 * chunk_index)


@celery.task(bind=True)
def async_save_selected_strava_activities(self, strava_account_id, strava_activity_ids, handle_overlap='existing'):
  strava_acct = StravaImportStorage.query.get(strava_account_id)
  saved_strava_activity_ids = [saved_activity.strava_id for saved_activity in strava_acct.activities.all()]

  run_in_parallel = group(
    async_save_strava_activity.s(
      strava_account_id,
      strava_activity_id,
      handle_overlap=handle_overlap
    )
    for strava_activity_id in strava_activity_ids
    if strava_activity_id not in saved_strava_activity_ids
  )

  return run_in_parallel.delay()
