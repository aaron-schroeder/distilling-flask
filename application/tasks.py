import datetime

import dateutil
import pandas as pd
from scipy.interpolate import interp1d
from sqlalchemy.exc import IntegrityError

from application import celery, converters
from application.models import db, Activity, StravaAccount
from application.plotlydash.dashboard_activity import calc_power
import power.util as putil


@celery.task
def async_save_strava_activities(account_id, activity_ids=[]):

  strava_acct = StravaAccount.query.get(account_id)
  client = strava_acct.client

  if activity_ids == 'all':
    # Get all activity ids (assumes everything is a valid run rn)
    activity_ids = [activity.id for activity in client.get_activities()]

  print(f'Num. of activities retrieved: {len(activity_ids)}')

  # Get data for each activity and create an entry in db.
  activities = []
  for activity_id in activity_ids:
    activity_data = client.get_activity(activity_id).to_dict()

    if activity_data['type'] not in ('Run', 'Walk', 'Hike'):
      print(f"Throwing out a {activity_data['type']}")
      continue

    df = converters.from_strava_streams(client.get_activity_streams(
      activity_id,
      types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
          'heartrate', 'cadence', 'watts', 'temp', 'moving',
          'grade_smooth']
    ))
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
    else:
      intensity_factor = None
      tss = None

    activities.append(Activity(
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

  try:
    print(f'Saving {len(activities)} runs/walks/hikes.')
    db.session.add_all(activities)
    db.session.commit()

  except IntegrityError as e:
    print('There was an error saving the activities.')
    print(e)
