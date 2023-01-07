import datetime
import uuid

import dash
from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask_login import current_user
import dateutil
import pandas as pd
from stravalib import Client

from application import converters, util
from application.models import db, Activity, StravaAccount
from sqlalchemy.exc import IntegrityError
from application.plotlydash import dashboard_activity
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from application.plotlydash.util import layout_login_required


dash.register_page(__name__, path_template='/strava/<activity_id>',
  title='Strava Activity Dashboard', name='Strava Activity Dashboard')


@layout_login_required
def layout(activity_id=None, **queries):
  if not current_user.has_authorized:
    return dcc.Location(pathname='/strava/authorize', id=str(uuid.uuid4()))

  strava_acct_id = queries.get('id') or queries.get('strava_id')

  if activity_id is None or strava_acct_id is None:
    return html.Div([])

  strava_account = StravaAccount.query.get(strava_acct_id)
  # token = current_user.strava_account.get_token()
  token = strava_account.get_token()
  client = Client(access_token=token['access_token'])

  activity = client.get_activity(activity_id)

  # Read the Strava json response into a DataFrame and perform
  # additional calculations on it.
  df = converters.from_strava_streams(client.get_activity_streams(
    activity_id,
    types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
      'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth']
  ))
  dashboard_activity.calc_power(df)

  out = dbc.Container(
    [
      html.Div(id='strava-stats'),
      StatsDivAIO(df=df, aio_id='strava'),
      FigureDivAIO(df=df, aio_id='strava'),
      dcc.Store(id='strava-summary-response', data=activity.to_dict()),
    ],
    id='dash-container',
    fluid=True,
  )

  return out


@callback(
  Output('save-result', 'children'),
  Input('save-activity', 'n_clicks'),
  State(FigureDivAIO.ids.store('strava'), 'data'),
  State('strava-summary-response', 'data'),
  State(StatsDivAIO.ids.intensity('strava'), 'value'),
  State(StatsDivAIO.ids.tss('strava'), 'value'),
  prevent_initial_call=True
)
def save_activity(
  n_clicks, 
  record_data,
  activity_data,
  intensity_factor,
  tss
):
  """Create database record for activity and save data files."""
  if (
    n_clicks is None
    or n_clicks == 0
    or record_data is None
    or activity_data is None
  ):
    raise PreventUpdate

  # Create a new activity record in the database
  try:
    new_act = Activity(
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
    )
    db.session.add(new_act)
    db.session.commit()

  except IntegrityError as e:
    print(e)
    return html.Div([
      'There was an error saving this activity.'
    ])

  return f'Activity saved successfully! Internal ID = {new_act.id}'
  # return dcc.Location(id=new_act.id, pathname=f'/dash/saved-activity/{new_act.id}')


@callback(
  Output('strava-stats', 'children'),
  Input('strava-summary-response', 'data'),
)
def update_stats(activity_data):
  """Fill the `strava-stats` div with Strava's summary data."""
  if activity_data is None:
    raise PreventUpdate

  return [
    html.H2(f"{activity_data['name']} ({activity_data['start_date_local']})"),
    dbc.Row([
      # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
      dbc.Col(f"{activity_data['elapsed_time']} sec (total)"),
      dbc.Col(f"{activity_data['total_elevation_gain'] * util.FT_PER_M:.0f} ft (gain)"),
      # dbc.Col(f"{activity_data['moving_time']} sec (moving)"),
    ]),
    html.Div(activity_data['description']),
    dbc.Row([
      dbc.Col(dbc.Button('Save activity to DB', id='save-activity')),
      dbc.Col(id='save-result')
    ]),
    html.Hr(),
  ]

  #     'start_date', 'gear_id',
  #     'average_cadence', 'average_heartrate',
  #     'calories', 'device_name', 'gear', 'segment_efforts',
  #     'splits_metric', 'splits_standard', 'laps', 'best_efforts'


@callback(
  Output(StatsDivAIO.ids.table('strava'), 'data'),
  Output(StatsDivAIO.ids.table('strava'), 'columns'),
  Input('strava-summary-response', 'data'),
  State(StatsDivAIO.ids.table('strava'), 'data'),
)
def add_strava_stats_to_table(activity_data, table_records):
  df_stats = pd.DataFrame.from_records(table_records)
  # df_stats.index = df_stats['']

  strava_row = pd.Series([], dtype='object')
  strava_row[''] = 'Strava'
  strava_row['Distance (m)'] = activity_data['distance']
  strava_row['Time (s)'] = activity_data['moving_time']
  strava_row['Speed (m/s)'] = activity_data['average_speed']
  strava_row['Pace'] = util.speed_to_pace(activity_data['average_speed'])
  strava_row['Time'] = util.seconds_to_string(activity_data['moving_time'])
  strava_row['Distance (mi)'] = activity_data['distance'] / util.M_PER_MI
  
  df_stats = df_stats.append(strava_row, ignore_index=True)

  return (
    df_stats.to_dict('records'),
    StatsDivAIO._create_moving_table_cols(df_stats.columns)
  )
