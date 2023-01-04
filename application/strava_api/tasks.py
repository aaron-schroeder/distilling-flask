import datetime

import dateutil
import pandas as pd
from scipy.interpolate import interp1d
from sqlalchemy.exc import IntegrityError

from application import celery, converters, stravatalk
from application.models import db, Activity
from application.plotlydash.dashboard_activity import calc_power
import power.util as putil


@celery.task
def async_save_all_activities(token):
  # Get all activity ids (assumes everything is a valid run rn)
  activity_ids = []
  page = 1
  while True:
    try:
      activity_json_next = stravatalk.get_activities_json(
        token['access_token'],
        page=page,
        limit=200
      )
    except Exception:
      print(f'exception on page {page}')
      break
    if len(activity_json_next) == 0:
      print(f'Reached end of activities.')
      print(f'(Page: {page}, '
            f'per page: 200)')
      break
    activity_ids.extend([
      activity['id'] for activity in activity_json_next
    ])
    page += 1
  print(f'Num. of activities retrieved: {len(activity_ids)}')

  # Get data for each activity and create an entry in db.
  activities = []
  for activity_id in activity_ids:
    stream_json = stravatalk.get_activity_streams_json(
      activity_id, 
      token['access_token']
    )
    df = converters.from_strava_streams(stream_json)
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

    activity_data = stravatalk.get_activity_json(
      activity_id, 
      token['access_token']
    )

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
      distance_m=activity_data['distance'],
      elevation_m=activity_data['total_elevation_gain'],
      intensity_factor=intensity_factor,
      tss=tss,
    ))

  try:
    db.session.add_all(activities)
    db.session.commit()

  except IntegrityError as e:
    print('There was an error saving the activities.')
    print(e)
