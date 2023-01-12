import datetime

import dateutil
import pandas as pd
from scipy.interpolate import interp1d
from sqlalchemy.exc import IntegrityError
from stravalib.exc import RateLimitExceeded

from application import celery, converters
from application.models import db, Activity, StravaAccount
from application.plotlydash.dashboard_activity import calc_power
import power.util as putil


@celery.task(
  bind=True,
  # autoretry_for=(RateLimitExceeded,),
  # retry_backoff=True,
  # retry_kwargs={'countdown': 5}
)
def async_save_strava_activity(self, account_id, activity_id, handle_overlap='existing'):

  strava_acct = StravaAccount.query.get(account_id)
  client = strava_acct.client
  
  try:
    activity = client.get_activity(activity_id)
  except RateLimitExceeded:
    self.retry()

  if activity.type not in ('Run', 'Walk', 'Hike'):
    print(f"Throwing out a {activity_data['type']}")
    return

  # check for saved activity with identical strava id;
  # if it exists, skip saving the new activity
  if Activity.query.filter_by(strava_id=activity.id).count():
    print(f'Saved activity with strava id {activity.id} already exists...skipping.')
    return

  # check for overlapping saved activities and handle accordingly
  overlap_ids = Activity.find_overlap_ids(
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
        db.session.delete(Activity.query.get(saved_activity_id))
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
    self.retry()

  intensity_factor = None
  tss = None

  if activity_streams:
    df = converters.from_strava_streams(activity_streams)
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
      ngp_ms = putil.lactate_norm(ngp_rolling[29:])

      cp_ms = 1609.34 / (6 * 60 + 30)  # 6:30 mile
      intensity_factor = ngp_ms / cp_ms

      total_hours = (df['time'].iloc[-1] - df['time'].iloc[0]) / 3600
      tss = 100.0 * total_hours * intensity_factor ** 2
    elif 'speed' in df.columns:
      # TODO: Add capabilities for flat-ground TSS.
      pass

  activity_data = activity.to_dict()

  db.session.add(Activity(
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
