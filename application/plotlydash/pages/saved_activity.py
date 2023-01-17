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


def layout(activity_id=None):
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

  return dbc.Container(
    [
      html.Div(id='model-stats'),
      StatsDivAIO(df=df, aio_id='saved'),
      FigureDivAIO(df=df, aio_id='saved'),
      dcc.Store(id='activity-id', data=activity_id),
    ],
    id='dash-container',
  )


@callback(
  Output('model-stats', 'children'),
  Input('activity-id', 'data'),
)
def update_stats(activity_id):
  """Fill the div with Activity model data."""
  if activity_id is None:
    raise PreventUpdate

  activity = Activity.query.get(activity_id)

  elapsed_time_str = units.seconds_to_string(
    activity.elapsed_time_s,
    show_hour=True
  )

  children = [
    html.H2(f"{activity.title} ({activity.recorded})"),
    dbc.Row([
      # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
      dbc.Col(f"Elapsed time: {elapsed_time_str}"),
      dbc.Col(f"Gain: {activity.elevation_m * units.FT_PER_M:.0f} ft"),
      dbc.Col(f"TSS: {activity.tss:.0f} (IF: {activity.intensity_factor:.2f})"),
    ]),
    html.Div(activity.description),
    html.Hr(),
  ]

  return children

