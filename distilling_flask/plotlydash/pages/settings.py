import dash
from dash import html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from distilling_flask.models import db, UserSettings
from distilling_flask.plotlydash.aio_components import TimeInput, SettingsLabel
from distilling_flask.plotlydash.layout import SettingsContainer
from distilling_flask.util import units
from distilling_flask.util.feature_flags import flag_set


dash.register_page(__name__, path_template='/settings',
  title='User Settings', name='User Settings')


def load_user_settings():
  if flag_set('ff_rename'):
    return UserSettings(cp_ms=float(str(UserSettings.cp_ms.server_default.arg)))
  else:
    return db.session.scalars(db.select(UserSettings)).first()
  

def layout(**_):

  user_settings = load_user_settings()

  return SettingsContainer(
    dbc.Form(
      [
        dbc.Row(
          [
            SettingsLabel('Critical Pace (CP)', html_for='cp-user'),
            dbc.Col(dbc.InputGroup([
              TimeInput(
                id='cp-user',
                seconds=units.M_PER_MI / user_settings.cp_ms,
              ),
              dbc.InputGroupText('per mile')
            ]))
          ],
          class_name='mb-2'
        ),
        dbc.Row(
          [
            SettingsLabel('Fundamental Threshold Pace (FTP)', html_for='ftp-user'),
            dbc.Col(dbc.InputGroup([
              TimeInput(
                id='ftp-user',
                seconds=units.M_PER_MI / user_settings.ftp_ms,
                disabled=True,
              ),
              dbc.InputGroupText('per mile')
            ])),
          ],
          class_name='mb-2'
        ),
        dbc.Row(
          dbc.Col(
            dbc.Button('Update settings', id='update-user', n_clicks=0)
          )
        ),
        dbc.Toast(
          id='status-popup',
          header='Success',
          is_open=False,
          dismissable=True,
          duration=4000,
          icon='success',
          # top: 66 positions the toast below the navbar
          style={'position': 'fixed', 'top': 66, 'right': 10, 'width': 350},
        ),
      ],
      action='',
      class_name='mt-2'
    ),
    page_title='User Settings'
  )


@callback(
  Output('ftp-user', 'value'),
  Input('cp-user', 'value')
)
def update_ftp(cp_str):
  if not cp_str:
    raise PreventUpdate
  return cp_str


@callback(
  Output('status-popup', 'children'),
  Output('status-popup', 'is_open'),
  Output('status-popup', 'header'),
  Output('status-popup', 'icon'),
  Input('update-user', 'n_clicks'),
  State('cp-user', 'value')
)
def update_user(n_clicks, cp_string):
  if not n_clicks:
    raise PreventUpdate

  user_settings = load_user_settings()
  user_settings.cp_ms = units.pace_to_speed(cp_string)

  try:
    db.session.commit()
  except:
    return (
      'I was not able to update your settings. Please try again later.',
      True,
      'Error',
      'danger'
    )
  else:
    return 'Your user profile has been updated.', True, 'Success', 'success'