from functools import wraps
from urllib.parse import quote
import uuid

import dash
from dash import Dash, dcc, html, page_registry
import dash_bootstrap_components as dbc

from distilling_flask.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from distilling_flask.util.dataframe import calc_power


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