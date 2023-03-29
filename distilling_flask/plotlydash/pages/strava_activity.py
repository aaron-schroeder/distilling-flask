import datetime
import uuid

import dash
from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dateutil
import pandas as pd
from sqlalchemy.exc import IntegrityError

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaImportStorage, StravaApiActivity
from distilling_flask.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from distilling_flask.util import readers, units
from distilling_flask.util.dataframe import calc_power


dash.register_page(__name__, path_template='/strava/activity/<activity_id>',
  title='Strava Activity Dashboard', name='Strava Activity Dashboard')


def layout(activity_id=None, **queries):
  strava_acct = StravaImportStorage.query.get(queries.get('id') or queries.get('strava_id'))

  if activity_id is None or strava_acct is None:
    return dbc.Container([])  # TODO: add help text

  client = strava_acct.client

  activity = client.get_activity(activity_id)

  if activity.type not in ['Run', 'Walk', 'Hike']:
    return dbc.Container(
      f'Unsupported activity type "{activity.type}". '
      'Currently supported activity types are Run, Walk, and Hike.'
    )
  
  # Read the Strava json response into a DataFrame and perform
  # additional calculations on it.
  df = readers.from_strava_streams(client.get_activity_streams(
    activity_id,
    types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
      'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth']
  ))
  calc_power(df)

  existing_activity = strava_acct.activities.filter_by(strava_id=activity_id).first()

  if existing_activity:
    button_col = dbc.Col(
      dcc.Link(
        dbc.Button('View Saved Activity'),
        href=existing_activity.relative_url
      )
    )
  else:
    button_col = dbc.Col([
      dbc.Button(
        'Import Activity',
        id='save-activity'
      ),
      dbc.Popover(
        id='save-result',
        is_open=False,
        target='save-activity',
      ),
    ])

  return dbc.Container(
    [
      html.Div(id='strava-stats'),
      dbc.Row(button_col, class_name='mb-3'),
      StatsDivAIO(df=df, aio_id='strava'),
      FigureDivAIO(df=df, aio_id='strava'),
      dcc.Store(id='strava-summary-response', data=activity.to_dict()),
    ],
    id='dash-container',
    fluid=True,
  )


@callback(
  Output('save-result', 'children'),
  Output('save-result', 'is_open'),
  Input('save-activity', 'n_clicks'),
  State(FigureDivAIO.ids.store('strava'), 'data'),
  State('strava-summary-response', 'data'),
  State(StatsDivAIO.ids.ngp('strava'), 'value'),
  prevent_initial_call=True
)
def save_activity(
  n_clicks, 
  record_data,
  activity_data,
  ngp_string,
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
    new_act = StravaApiActivity(
      title=activity_data['name'],
      description=activity_data['description'],
      created=datetime.datetime.utcnow(),  
      recorded=dateutil.parser.isoparse(activity_data['start_date']),
      tz_local=activity_data['timezone'],
      moving_time_s=activity_data['moving_time'],
      elapsed_time_s=activity_data['elapsed_time'],
      # Fields below here not required
      strava_id=activity_data['id'],
      strava_acct_id=activity_data['athlete']['id'],
      distance_m=activity_data['distance'],
      elevation_m=activity_data['total_elevation_gain'],
      ngp_ms=units.pace_to_speed(ngp_string),
    )
    db.session.add(new_act)
    db.session.commit()

  except IntegrityError as e:
    return f'There was an error saving this activity: {e}', True

  return dcc.Location(pathname=f'/saved/{new_act.id}', id=str(uuid.uuid4())), True


@callback(
  Output('strava-stats', 'children'),
  Input('strava-summary-response', 'data'),
)
def update_stats(activity_data):
  """Fill the `strava-stats` div with Strava's summary data."""
  if activity_data is None:
    raise PreventUpdate

  elapsed_time_str = units.seconds_to_string(
    activity_data['elapsed_time'],
    show_hour=True
  )
  gain_ft = activity_data['total_elevation_gain'] * units.FT_PER_M

  return [
    html.H1(f"{activity_data['name']} ({activity_data['start_date_local']})"),
    dbc.Row([
      # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
      dbc.Col(f"Elapsed time: {elapsed_time_str}"),
      dbc.Col(f"Gain: {gain_ft:.0f} ft"),
    ]),
    html.Div(activity_data['description']),
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
  strava_row['Pace'] = units.speed_to_pace(activity_data['average_speed'])
  strava_row['Time'] = units.seconds_to_string(activity_data['moving_time'])
  strava_row['Distance (mi)'] = activity_data['distance'] / units.M_PER_MI
  
  df_stats = df_stats.append(strava_row, ignore_index=True)

  return (
    df_stats.to_dict('records'),
    StatsDivAIO._create_moving_table_cols(df_stats.columns)
  )
