import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html


MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'
POWER_ID = 'power'


def create_x_stream_radiogroup(opts, value=None):
  value = value or opts[0]

  return dbc.FormGroup([
    dbc.Label('Select x-axis stream:'),
    dbc.RadioItems(
      options=[{'label': x, 'value': x} for x in opts],
      value=value,
      id='x-selector',
      inline=True
    ),
  ])


def create_plot_checkgroup(opts, values=None):
  values = values or opts

  return dbc.FormGroup([
    dbc.Label('Select visible plots:'),
    dbc.Checklist(
      options=[{'label': x, 'value': x} for x in opts],
      value=values,
      id='plot-checklist',
      inline=True
    ),
  ])


def init_layout():
  """Dumb layout - does not change based on what data is available."""
  out = dbc.Container(
    [
      html.Div(id='stats'),
      dbc.Row(id='plot-options'),
      html.Div(id='figures'),
      dcc.Store(id='activity-data'), # data streams
      dcc.Store(id='activity-stats'), # could be strava response etc
      dcc.Store(id='calc-stats'), # storage for DF-to-stats calc
    ],
    id='dash-container',
    fluid=True,
  )

  return out