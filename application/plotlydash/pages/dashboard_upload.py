"""Display data from an uploaded activity or route file.

Basically want to have an encapsulated demo that I can deploy to
pythonanywhere etc. I have built cool stuff, but it is hard to show
my work!

https://dash.plotly.com/dash-core-components/upload

dcc.Upload properties:
https://dash.plotly.com/dash-core-components/upload#dcc.upload-component-properties

No saving the file for now - keep as a DataFrame in memory.
(Opportunity to use redis?)
"""
import base64
import datetime
import io
import json
import os

import dash
from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask_login import current_user
import pandas as pd

from application import converters
from application.plotlydash import dashboard_activity
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from application.plotlydash.util import layout_login_required


dash.register_page(__name__, path_template='/upload',
  title='Analyze an activity file', name='Analyze an activity file')


@layout_login_required
def layout():

  return dbc.Container([
    dcc.Upload(
      id='upload-data',
      # children=html.Div([
      children=[
        'Drag and Drop or ',
        html.A('Select File')
      ],
      # ]),
      style={
        'width': '100%',
        'height': '60px',
        'lineHeight': '60px',
        'borderWidth': '1px',
        'borderStyle': 'dashed',
        'borderRadius': '5px',
        'textAlign': 'center',
        'margin': '10px 0px'
      },
      # Allow multiple files to be uploaded?
      multiple=False,
    ),
    html.Div(id='file-stats'),
    html.Div(id='stats-container'),
    html.Div(id='figure-container'),
  ])

  # --- Stopped periods callback experiment ----------------

  # # Can I create a gray background to visually tie these together?
  # # (Maybe remove the Hr then)
  # app.layout.children.extend([
  #   html.Hr(),
  #   html.H3('Stopped periods'),
  #   html.Div(id='clickdata'),
  #   dbc.Row([
  #     dbc.Col(
  #       [
  #         dbc.FormGroup([
  #           dbc.Label('From:'),
  #           dbc.Input(
  #             type='number', 
  #             id='stop-start-0',
  #             min=0, max=10000,
  #             placeholder='Beginning record'
  #           )
  #         ]),
  #       ],
  #       width=2,
  #     ),
  #     dbc.Col(
  #       [
  #         dbc.FormGroup([
  #           dbc.Label('To:'),
  #           dbc.Input(
  #             type='number', 
  #             id='stop-stop-0',
  #             min=0, max=10000,
  #             placeholder='End record'
  #           )
  #         ]),
  #       ],
  #       width=2,
  #     ),
  #   ]),
  #   dbc.Button('Update', id='update-stops', color='primary')
  # ])

  # @app.callback(
  #   Output('clickdata', 'children'),
  #   # In reality it is this:
  #   # Output('figures', 'children'),
  #   # Output('stats', 'children'),
  #   Input('update-stops', 'n_clicks'),
  #   State('stop-start-0', 'value'),
  #   State('stop-stop-0', 'value')
  # )
  # def update_stopped_periods(_, begin_index, end_index):
  #   if isinstance(begin_index, int) and isinstance(end_index, int):
  #     if begin_index <= end_index:
  #       return f'From {begin_index} to {end_index}.'

  # ------------------------------------------------------

  # Not sure what I would do with this, but here.
  # app.layout.children.insert(1, html.Div(id='data'))
  # @app.callback(
  #   Output('data', 'children'),
  #   Input(layout.SPEED_ID, 'selectedData')
  # )
  # def show_me_selected_data(data):
  #   # return data['points'][0]['pointNumber']
  #   return str(data)


@callback(
  Output('stats-container', 'children'),
  Output('figure-container', 'children'),
  Input('upload-data', 'contents'),
  State('upload-data', 'filename'),
  # State('upload-data', 'last_modified'),
)
def get_file_data(contents, fname):
  if contents is None:
    raise PreventUpdate

  df = parse_contents(contents, fname)

  if df is None:
    raise PreventUpdate

  # Add calcd fields to the DataFrame.
  dashboard_activity.calc_power(df)

  return (
    StatsDivAIO(df=df, aio_id='upload'),
    FigureDivAIO(df=df, aio_id='upload'),
  )


@callback(
  Output('file-info', 'children'),
  Input('upload-data', 'filename'),
  State('upload-data', 'last_modified'),
)
def update_file_info(fname, date):
  if fname is None or date is None:
    raise PreventUpdate

  stats = html.Div([
    html.H5(fname),
    html.H6(datetime.datetime.fromtimestamp(date)),
    html.Hr(),
  ])

  return stats


def parse_contents(contents, filename):
 
  content_type, content_string = contents.split(',')

  decoded = base64.b64decode(content_string)

  if filename.lower().endswith('json'):
    data_json = json.loads(decoded.decode('utf-8'))

    # Assume the user uploaded strava stream json output
    return converters.from_strava_streams(data_json)

  elif filename.lower().endswith('fit'):
    return converters.from_fit(decoded)
  
  elif filename.lower().endswith('csv'):
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))

  elif filename.lower().endswith('tcx'):
    return converters.from_tcx(decoded)

  elif filename.lower().endswith('gpx'):
    return converters.from_gpx(decoded)
