import datetime

import dash
from dash import dcc, html, callback, Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

from application import util
from application.models import db, Activity
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO


dash.register_page(__name__, path_template='/saved/<activity_id>',
  title='Saved Activity Dashboard', name='Saved Activity Dashboard')


def layout(activity_id=None):
  if activity_id is None:
    return html.Div([])

  activity = Activity.query.get(activity_id)
  
  df = pd.read_csv(activity.filepath_csv)

  activity_dict = {
    k: f if not isinstance(f, datetime.date) else f.isoformat()
    for k, f in activity.__dict__.items() if not k.startswith('_')
  }

  # Initialize an empty layout to be populated with callback data.
  # TODO: Bring this part of layout in here? Plotter can fill it...
  # app.layout = LAYOUT
  return dbc.Container(
    [
      html.Div(id='model-stats'),
      StatsDivAIO(df=df, aio_id='saved'),
      FigureDivAIO(df=df, aio_id='saved'),
      dcc.Store(id='activity-stats', data=activity_dict),
    ],
    id='dash-container',
    fluid=True,
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
      dbc.Col(f"{activity_data['elapsed_time_s']} sec (total)"),
      dbc.Col(f"{activity_data['elevation_m'] * util.FT_PER_M:.0f} ft (gain)"),
      # dbc.Col(f"{activity_data['moving_time']} sec (moving)"),
      dbc.Col(f"{activity_data['tss']} ({activity_data['intensity_factor']})"),
    ]),
    html.Div(activity_data['description']),
    html.Hr(),
  ]

  return children

