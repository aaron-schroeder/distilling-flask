import uuid

import dash
from dash import dcc, html, callback, Input, Output, State, ALL
import dash_bootstrap_components as dbc
from flask_login import login_user

from application.models import AdminUser


dash.register_page(__name__, path_template='/login',
  title='Log in', name='Log in')


def layout(**kwargs):
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
            # dbc.FormFeedback('Correct password', type='valid'),
            dbc.FormFeedback('Incorrect password', type='invalid')
          ])),
          dbc.Col(
            dbc.Button('Log in', id='login', n_clicks=0)
          )
        ],
        justify='center',
      ),
      action='',
    ),
    html.Div(id='location-dummy')
  ])


@callback(
  Output('location-dummy', 'children'),
  Output('password', 'invalid'),
  Input('login', 'n_clicks'),
  State('password', 'value')
)
def validate_password(n_clicks, password):
  if n_clicks and n_clicks > 0:
    user = AdminUser()
    if user.check_password(password):
      # Login and redirect to admin landing page.
      login_user(user, remember=True)
      return dcc.Location(pathname='/admin', id=str(uuid.uuid4())), False
    else:
      return None, True
  return None, False
