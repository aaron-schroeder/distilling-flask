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
    assets_external_path='https://cdn.jsdelivr.net/gh/aaron-schroeder'
                         '/shared-assets@main/',
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
