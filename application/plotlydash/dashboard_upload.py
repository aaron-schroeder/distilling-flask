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

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc

import pandas as pd

from application import converters
from application.plotlydash import layout
from application.plotlydash.dashboard_activity import create_rows, init_hover_callbacks


def create_dash_app(mode='basic'):

  external_stylesheets = [dbc.themes.BOOTSTRAP]

  app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

  app.layout = layout.LAYOUT

  app.layout.children.insert(
    0,
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
  )

  @app.callback(
    Output('figures', 'children'),
    Input('upload-data', 'contents'),  # binary string
    Input('x_stream', 'value'),
    State('upload-data', 'filename'),
    State('upload-data', 'last_modified'),
  )
  def update_output(contents, x_stream, name, date):

    if contents is not None:
      children = [
        parse_contents(
          contents,
          name,
          date,
          x_stream
        )
      ]
      return children

  init_hover_callbacks(app)

  return app


def parse_contents(contents, filename, date, x_stream_label=None):
  content_type, content_string = contents.split(',')

  decoded = base64.b64decode(content_string)
  try:
    if filename.lower().endswith('json'):
      data_json = json.loads(decoded.decode('utf-8'))

      # Assume the user uploaded strava stream json output
      df = converters.from_strava_streams(data_json)

    elif filename.lower().endswith('fit'):
      df = converters.from_fit(decoded)
    
    elif filename.lower().endswith('csv'):
      df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    elif filename.lower().endswith('tcx'):
      from application.converters import from_tcx
      df = converters.from_tcx(io.BytesIO(decoded))

    elif filename.lower().endswith('gpx'):
     from application.converters import from_gpx
     df = converters.from_gpx(io.BytesIO(decoded))

    else:
      return html.Div([
        html.H5(filename),
        'File type not supported.'
      ])
  
  except Exception as e:
    print(e)
    return html.Div([
      'There was an error processing this file.'
    ])

  if x_stream_label == 'record':
    x_stream_label = None

  # figure_rows = []
  figure_rows = create_rows(df, x_stream_label=x_stream_label)

  return html.Div(
    [
      html.H5(filename),
      html.H6(datetime.datetime.fromtimestamp(date)),
    ] + figure_rows
  )

# Uncomment this to turn on advanced stuff.
# from application.plotlydash.dashboard_next import init_hover_callbacks, parse_contents

if __name__ == '__main__':
    app.run_server(debug=True)