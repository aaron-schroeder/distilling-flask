from functools import wraps

from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
from flask_login import current_user

from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from application.util.dataframe import calc_power


def layout_login_required(layout_func):
  @wraps(layout_func)
  def decorated_function(*args, **kwargs):
    if not current_user.is_authenticated:
      return dcc.Location(pathname='/login')
    return layout_func(*args, **kwargs)
  return decorated_function


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