from dash import Dash
import dash_bootstrap_components as dbc
from specialsauce.sources import minetti, strava, trainingpeaks

from application.plotlydash.figure_layout import GRADE, SPEED
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO


def create_dash_app(df):
  """Construct single-page Dash app for activity data display from DF.
  
  Mostly for debugging purposes.

  Args:
    df (pandas.DataFrame): Activity data, with each row a record, and
      each column a data stream.
  """
  app = Dash(
    __name__,
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
    ],
    
    # Script source: local download of the plotly mapbox distribution.
    # Since the script is in assets/ and supplies the global Plotly var,
    # it is used over the other plotly packages by default.
    # (Modified to make my programmatic hover-on-map stuff work). 
    # It includes everything I need:
    # scatter, scattermapbox, choroplethmapbox and densitymapbox
    # https://github.com/plotly/plotly.js/blob/master/dist/README.md#partial-bundles

    # Turn this on to avoid using local scripts by loading from cdn.
    # Note: Local scripts are by default from `async-plotlyjs.js`, which is
    # minified and incomprehensible when debugging. Using plotly-mapbox,
    # for example, allows me to see what is going on for easier debugging
    # and future edits to the script itself.
    # https://community.plotly.com/t/smaller-version-of-async-plotlyjs-js-its-so-big-and-loads-so-slow/42247/2
    # https://github.com/plotly/dash-docs/issues/723#issuecomment-656393396
    # https://github.com/plotly/plotly.js/blob/master/dist/README.md#partial-bundles
    # external_scripts=[
    #   #'https://cdn.plot.ly/plotly-basic-1.54.3.min.js',
    #   'https://cdn.plot.ly/plotly-mapbox-1.58.4.js'
    # ],
  )

  calc_power(df)

  app.layout = dbc.Container(
    [
      StatsDivAIO(df=df, aio_id='df'),
      FigureDivAIO(df=df, aio_id='df'),
    ],
    id='dash-container',
    fluid=True,
  )

  return app


def calc_power(df):
  """Add grade-adjusted speed columns to the DataFrame."""
  if df.fld.has(SPEED, GRADE):
    df['equiv_speed'] = df[SPEED] * minetti.cost_of_running(df[GRADE]/100) / minetti.cost_of_running(0.0)
    df['NGP'] = df[SPEED] * trainingpeaks.ngp_speed_factor(df[GRADE]/100)
    df['GAP'] = df[SPEED] * strava.gap_speed_factor(df[GRADE]/100)
