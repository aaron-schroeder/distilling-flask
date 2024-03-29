import dash
from dash import html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask import get_flashed_messages, url_for

from application.models import db, StravaAccount
from application.plotlydash.aio_components import StravaAccountRow
from application.plotlydash.layout import SettingsContainer
from application.plotlydash.util import layout_login_required
from application.util import units


dash.register_page(__name__, path_template='/settings/strava',
  title='Manage Strava Accounts', name='Manage Strava Accounts')


@layout_login_required
def layout(**_):

  strava_account_rows = [
    StravaAccountRow(strava_account) 
    for strava_account in StravaAccount.query.all()
  ]

  connect_btn_text = (
    'Connect Another Strava Account' 
    if len(strava_account_rows)
    else 'Connect a Strava Account'
  )
  connect_btn_row = dbc.Row(
    dbc.Button(
      href=url_for('strava_api.authorize'),
      color='primary',
      class_name='mt-4',
      external_link=True,
      children=[
        html.I(className='fa-solid fa-plus'),
        f' {connect_btn_text}',
      ],
    ),
    justify='center', # verify this sets justify-content-center
  )

  content = [
    # <div class="alert"> for each message in get_flashed_messages
    connect_btn_row,
  ] + strava_account_rows

  return SettingsContainer(content, page_title='Manage Strava Accounts')
