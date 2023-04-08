import os

import dash
from dash import dcc, html, callback, Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from stravalib.exc import RateLimitExceeded

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaApiActivity
from distilling_flask.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from distilling_flask.util import dataframe, readers, units
from distilling_flask.util.feature_flags import flag_set


dash.register_page(__name__, path_template='/saved/<activity_id>',
  title='Saved Activity Dashboard', name='Saved Activity Dashboard')


def layout(activity_id=None, **_):
  if activity_id is None:
    return html.Div([])

  activity = db.session.get(StravaApiActivity, activity_id)

  elapsed_time_str = units.seconds_to_string(
    activity.elapsed_time_s, show_hour=True)

  layout_container = dbc.Container(
    [
      html.H1(activity.title),
      dbc.Row([
        dbc.Col(
          activity.recorded.strftime('%a, %m/%d/%Y %H:%M:%S'),
          width=12,
          md=4,
        ),
        # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
        dbc.Col(
          f"Elapsed time: {elapsed_time_str}",
          width=12,
          md=3,
        ),
        dbc.Col(
          f"Gain: {activity.elevation_m * units.FT_PER_M:.0f} ft",
          width=12,
          md=2,
        ),
        dbc.Col(
          f"TSS: {activity.tss:.0f} (IF: {activity.intensity_factor:.2f})"
            if activity.tss and activity.intensity_factor
            else 'TSS: ?? (IF: ??)',
          width=12,
          md=3,
        ),
      ]),
      html.Div(activity.description),
      html.Hr(),
    ],
    id='dash-container',
  )

  strava_account = activity.import_storage if flag_set('ff_rename') else activity.strava_acct
  if not flag_set('ff_rename') and (not strava_account or not strava_account.has_authorized):
    layout_container.children.append(html.Div(
      'The owner of this app is not currently granting '
      'permission to access their Strava data.'
    ))
    return layout_container

  if flag_set('ff_rename'):
    df = readers.from_strava_streams(activity.streams)
  else:
    client = strava_account.get_client()

    if flag_set('ff_rename'):
        df = readers.from_strava_streams(activity.streams)
    else:
      try:
        # activity_id = activity.id if flag_set('ff_rename') else activity.strava_id
        df = readers.from_strava_streams(client.get_activity_streams(
          activity_id,
          types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
            'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth']
        ))
      except RateLimitExceeded as e:
        layout_container.children.append(html.Div(
          f'Strava API rate limit exceeded: '
          f'{e.limit} requests in {e.timeout} seconds.'
        ))
        return layout_container

    # Add additional calculated columns to the DataFrame
    dataframe.calc_power(df)

  # # WIP
  #
  # activity_data = activity.summary
  # strava_row = pd.Series([], dtype='object')
  # strava_row[''] = 'Strava'
  # strava_row['Distance (m)'] = activity_data['distance']
  # strava_row['Time (s)'] = activity_data['moving_time']
  # strava_row['Speed (m/s)'] = activity_data['average_speed']
  # strava_row['Pace'] = units.speed_to_pace(activity_data['average_speed'])
  # strava_row['Time'] = units.seconds_to_string(activity_data['moving_time'])
  # strava_row['Distance (mi)'] = activity_data['distance'] / units.M_PER_MI
  
  # # We will be updating the data and columns here
  # stats_div = StatsDivAIO(df=df, aio_id='saved', className='mb-4')
  # df_stats = pd.DataFrame.from_records(stats_div.children[0].data)
  # # df_stats.index = df_stats['']
  # df_stats = df_stats.append(strava_row, ignore_index=True)
  # stats_div.children[0].data = df_stats.to_dict('records')

  layout_container.children.extend([
    StatsDivAIO(df=df, aio_id='saved', className='mb-4'),
    FigureDivAIO(df=df, aio_id='saved')])

  return layout_container


# @callback(
#   Output(StatsDivAIO.ids.table('saved'), 'data'),
#   Output(StatsDivAIO.ids.table('saved'), 'columns'),
#   Input('strava-summary-response', 'data'),
#   State(StatsDivAIO.ids.table('saved'), 'data'),
# )
# def add_strava_stats_to_table(activity_data, table_records):
#   pass