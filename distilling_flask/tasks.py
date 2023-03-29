import datetime
import math

from celery import group
import dateutil
import pandas as pd
from scipy.interpolate import interp1d
from sqlalchemy.exc import IntegrityError
from stravalib.exc import RateLimitExceeded

from distilling_flask import celery
from distilling_flask.models import db, AdminUser
from distilling_flask.io_storages.strava.models import StravaImportStorage, StravaApiActivity
from distilling_flask.util.dataframe import calc_power
from distilling_flask.util import power, readers


def est_15_min_rate(strava_client):
  # Whether we are rate-limited or not, we just got current info
  # on the rate limit status.
  rate_limit_status = strava_client.protocol.rate_limiter.rules[0].rate_limits

  # Create groups of activities to be added. 
  # Split into 15-minute waves (because of 15-min limit),
  # but ultimately decide the rate based on the daily limit.
  # (In the future, we can be smarter about which limit will
  # be hit first.)
  rate_hourly_max = min(
    (rate_limit_status['long']['limit'] - 5) / (24 * 3),
    (rate_limit_status['short']['limit']- 5) / (0.25 * 3)
  )
  
  return math.floor(rate_hourly_max * 0.25)


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

  num_15_max = est_15_min_rate(client)
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

  intensity_factor = None
  tss = None

  if activity_streams:
    df = readers.from_strava_streams(activity_streams)
    calc_power(df)

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

      total_seconds = df['time'].iloc[-1] - df['time'].iloc[0]

      tss = power.training_stress_score(
        ngp_scalar, AdminUser().settings.ftp_ms, total_seconds)
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
    intensity_factor=intensity_factor,
    tss=tss,
  ))

  db.session.commit()
