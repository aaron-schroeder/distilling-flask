"""Display data from an uploaded activity or route file.

No saving the file for now - keep as a DataFrame in memory.
(Opportunity to use redis?)
"""
import base64
import datetime
import io
import json

import dash
from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

from distilling_flask.plotlydash.aio_components import FigureDivAIO, StatsDivAIO
from distilling_flask.plotlydash.layout import SettingsContainer
from distilling_flask.util import readers
from distilling_flask.util.dataframe import calc_power


dash.register_page(__name__, path_template='/analyze-file',
  title='Analyze an activity file', name='Analyze an activity file')


def layout(**_):

  return SettingsContainer(
    [
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
    ],
    page_title='Analyze an Activity File'
  )

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
  calc_power(df)

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

  if filename.lower().endswith('fit'):
    return readers.from_fit(decoded)
  
  elif filename.lower().endswith('csv'):
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))

  elif filename.lower().endswith('tcx'):
    return readers.from_tcx(decoded)

  elif filename.lower().endswith('gpx'):
    return readers.from_gpx(decoded)

  # elif filename.lower().endswith('json'):
  #   data_json = json.loads(decoded.decode('utf-8'))
  #   # Assume the user uploaded strava stream json output
  #   return readers.from_strava_streams(data_json)

  else:
    raise TypeError(
      f'{filename} does not seem to be a file type that is accepted '
      'at this time (.fit, .tcx, .gpx)'
    )
