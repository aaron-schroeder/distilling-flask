import dash
from dash import html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from application.models import db, AdminUser
from application.plotlydash.aio_components import TimeInput, SettingsLabel
from application.plotlydash.layout import SettingsContainer
from application.plotlydash.util import layout_login_required
from application.util import units


dash.register_page(__name__, path_template='/settings',
  title='User Settings', name='User Settings')


@layout_login_required
def layout(**_):

  user_settings_cur = AdminUser().settings  # models.UserSettings instance

  return SettingsContainer(
    dbc.Form(
      [
        dbc.Row(
          [
            SettingsLabel('Critical Pace (CP)', html_for='cp-user'),
            dbc.Col(dbc.InputGroup([
              TimeInput(
                id='cp-user',
                seconds=units.M_PER_MI / user_settings_cur.cp_ms,
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
                seconds=units.M_PER_MI / user_settings_cur.ftp_ms,
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

  user_settings = AdminUser().settings
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