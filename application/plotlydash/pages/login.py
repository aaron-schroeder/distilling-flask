import uuid

import dash
from dash import dcc, html, callback, Input, Output, State, ALL
import dash_bootstrap_components as dbc
from flask_login import current_user, login_user

from application.models import AdminUser


dash.register_page(__name__, path_template='/login',
  title='Log in', name='Log in')


def layout(**url_queries):
  next_raw = url_queries.get('next')
  if next_raw:
    next_url = next_raw
  else:
    next_url = '/settings'

  if current_user.is_authenticated:
    return dcc.Location(pathname=next_url, id=str(uuid.uuid4()))

  return dbc.Container([
    dbc.Form(
      dbc.Row(
        [
          dbc.Label('Password', html_for='password', width='auto'),
          dbc.Col(html.Div([
            dbc.Input(
              id='password',
              type='password',
              placeholder='Enter password',
              # required=True
            ),
            dbc.FormFeedback('Incorrect password', type='invalid')
          ])),
          dbc.Col(
            dbc.Button('Log in', id='login', n_clicks=0)
          ),
          dcc.Store(id='next-url', data=next_url)
        ],
        justify='center',
      ),
      action='',
      class_name='mt-2'
    ),
    html.Div(id='location-dummy')
  ])


@callback(
  Output('location-dummy', 'children'),
  Output('password', 'invalid'),
  Input('login', 'n_clicks'),
  State('password', 'value'),
  State('next-url', 'data')
)
def validate_password(n_clicks, password, next_url):
  if n_clicks and n_clicks > 0:
    user = AdminUser()
    if user.check_password(password):
      login_user(user, remember=True)
      return dcc.Location(pathname=next_url, id=str(uuid.uuid4())), False
    else:
      return None, True
  return None, False
