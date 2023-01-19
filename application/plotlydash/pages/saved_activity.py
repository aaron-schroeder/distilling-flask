import datetime

import dash
from dash import dcc, html, callback, Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from application.models import Activity
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from application.util import dataframe, readers, units


dash.register_page(__name__, path_template='/saved/<activity_id>',
  title='Saved Activity Dashboard', name='Saved Activity Dashboard')


def layout(activity_id=None, **_):
  if activity_id is None:
    return html.Div([])

  activity = Activity.query.get(activity_id)

  strava_account = activity.strava_acct
  if not strava_account or not strava_account.has_authorized:
    return dbc.Container('This app\'s administrator is not currently granting '
                         'permission to access their Strava activities.')
  client = strava_account.client

  # Read the Strava response into a DataFrame and perform
  # additional calculations on it.
  df = readers.from_strava_streams(client.get_activity_streams(
    activity.strava_id,
    types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
      'heartrate', 'cadence', 'watts', 'temp', 'moving', 'grade_smooth']
  ))
  dataframe.calc_power(df)

  elapsed_time_str = units.seconds_to_string(
    activity.elapsed_time_s,
    show_hour=True
  )

  return dbc.Container(
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
          f"TSS: {activity.tss:.0f} (IF: {activity.intensity_factor:.2f})",
          width=12,
          md=3,
        ),
      ]),
      html.Div(activity.description),
      html.Hr(),
      StatsDivAIO(df=df, aio_id='saved', className='mb-4'),
      FigureDivAIO(df=df, aio_id='saved'),
      dcc.Store(id='activity-id', data=activity_id),
    ],
    id='dash-container',
  )
