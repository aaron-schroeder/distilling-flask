import datetime
import json
import os

import dash
from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dateutil
import pandas as pd

from application import converters, stravatalk, util
from application.plotlydash import dashboard_activity
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO


ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')

dash.register_page(__name__, path_template='/strava/<activity_id>',
  title='Strava Activity Dashboard', name='Strava Activity Dashboard')


def layout(activity_id=None):
  if activity_id is None:
    return html.Div([])

  stream_json = stravatalk.get_activity_streams_json(activity_id, ACCESS_TOKEN)

  activity_json = stravatalk.get_activity_json(activity_id, ACCESS_TOKEN)

  # Read the Strava json response into a DataFrame and perform
  # additional calculations on it.
  df = converters.from_strava_streams(stream_json)
  dashboard_activity.calc_power(df)

  out = dbc.Container(
    [
      html.Div(id='strava-stats'),
      StatsDivAIO(df=df, aio_id='strava'),
      FigureDivAIO(df=df, aio_id='strava'),
      dcc.Store(id='strava-summary-response', data=activity_json),
      dcc.Store(id='strava-stream-response', data=stream_json)
    ],
    id='dash-container',
    fluid=True,
  )

  return out


@callback(
  Output('save-result', 'children'),
  Input('save-activity', 'n_clicks'),
  State(FigureDivAIO.ids.store('strava'), 'data'),
  State('strava-stream-response', 'data'),
  State('strava-summary-response', 'data'),
  State(StatsDivAIO.ids.intensity('strava'), 'value'),
  State(StatsDivAIO.ids.tss('strava'), 'value'),
  prevent_initial_call=True
)
def save_activity(
  n_clicks, 
  record_data, 
  stream_list, 
  activity_data, 
  intensity_factor,
  tss
):
  """Create database record for activity and save data files."""
  if (
    n_clicks is None
    or n_clicks == 0
    or record_data is None
    or stream_list is None
    or activity_data is None
  ):
    raise PreventUpdate

  fname_json = f'application/activity_files/original/{activity_data["id"]}.json'
  fname_csv = f'application/activity_files/csv/{activity_data["id"]}.csv'

  # Create a new activity record in the database
  from application.models import db, Activity
  from sqlalchemy.exc import IntegrityError

  try:
    new_act = Activity(
      title=activity_data['name'],
      description=activity_data['description'],
      created=datetime.datetime.utcnow(),  
      recorded=dateutil.parser.isoparse(activity_data['start_date']),
      tz_local=activity_data['timezone'],
      moving_time_s=activity_data['moving_time'],
      elapsed_time_s=activity_data['elapsed_time'],
      filepath_orig=fname_json,
      filepath_csv=fname_csv,
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

  # Save the strava response json
  with open(fname_json, 'w') as outfile:
    json.dump(stream_list, outfile)

  # Save the processed DataFrame as CSV
  df = pd.DataFrame.from_records(record_data)
  df.to_csv(fname_csv)

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
      dbc.Col(
        dbc.Button('Save activity to DB', id='save-activity'),
        # align='center',
        # className='text-center',
      ),
      dbc.Col(
        id='save-result',
      )
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
