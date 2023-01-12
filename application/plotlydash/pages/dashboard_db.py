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

  activity_dict = {
    k: f if not isinstance(f, datetime.date) else f.isoformat()
    for k, f in activity.__dict__.items() 
    if not k.startswith('_') and not k == 'strava_acct'
  }

  return dbc.Container(
    [
      html.Div(id='model-stats'),
      StatsDivAIO(df=df, aio_id='saved'),
      FigureDivAIO(df=df, aio_id='saved'),
      dcc.Store(id='activity-stats', data=activity_dict),
    ],
    id='dash-container',
  )


@callback(
  Output('model-stats', 'children'),
  Input('activity-stats', 'data'),
)
def update_stats(activity_data):
  """Fill the div with Activity model data."""
  if activity_data is None:
    raise PreventUpdate

  children = [
    html.H2(f"{activity_data['title']} ({activity_data['recorded']})"),
    dbc.Row([
      # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
      dbc.Col(f"Elapsed time: {units.seconds_to_string(activity_data['elapsed_time_s'])}"),
      dbc.Col(f"Gain: {activity_data['elevation_m'] * units.FT_PER_M:.0f} ft"),
      # dbc.Col(f"{activity_data['moving_time']} sec (moving)"),
      dbc.Col(f"TSS: {activity_data['tss']:.0f} (IF: {activity_data['intensity_factor']:.2f})"),
    ]),
    html.Div(activity_data['description']),
    html.Hr(),
  ]

  return children

