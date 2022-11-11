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

from dash import Dash, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

import pandas as pd

from application import converters, util
from application.plotlydash import dashboard_activity
# from application.plotlydash.dashboard_activity import (
#   calc_power, create_moving_table, create_power_table,
#   create_rows, init_hover_callbacks
# )
from application.plotlydash import layout


def add_dashboard_to_flask(server):
  """Create a Plotly Dash dashboard with the specified server.

  This is actually used to create a dashboard that piggybacks on a
  Flask app, using that app its server.
  
  """
  dash_app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash-upload/',    
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
      # '/static/css/styles.css',  # Not yet.
    ],
  )

  # Initialize an empty layout to be populated with callback data.
  init_layout(dash_app)

  init_callbacks(dash_app)

  return dash_app.server


def create_dash_app():

  external_stylesheets = [dbc.themes.BOOTSTRAP]

  app = Dash(__name__, external_stylesheets=external_stylesheets)

  init_layout(app)

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

  init_callbacks(app)

  return app


def init_layout(app):
  app.layout = layout.init_layout()

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

  app.layout.children.insert(1, html.Div(id='file-stats'))


def init_callbacks(app):

  @app.callback(
    Output('activity-data', 'data'),
    # Output('activity-stats', 'data'), # need fileparsers for stats
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    # State('upload-data', 'last_modified'),
  )
  def get_file_data(contents, fname):
    if contents is not None:
      # try:

      # Change to "convert_to_df"
      df = parse_contents(contents, fname)

      # Return stats as a dict, nothing fancy
      # stats = get_file_stats(contents, fname)

      # except Exception as e:
      #   print(e)
        # return html.Div([
        #     'There was an error processing this file.'
        #   ]), None

      if df is None:
        return None
        # return html.Div([
        #   html.H5(fname),
        #   'File type not supported.'
        # ]), None

      # Add calcd fields to the DataFrame.
      dashboard_activity.calc_power(df)

      return df.to_dict('records')  # activity_json

  # Need to import update_figures from dashboard_activity.py,
  # and adapt it to work with df from records, not stream_list.
  # @app.callback(
  #   Output('figures', 'children'),
  #   Input('activity-data', 'data'),
  #   Input('x-selector', 'value')
  # )(update_figures)

  @app.callback(
    Output('save-dummy', 'children'),
    Input('save-activity', 'n_clicks'),
    State('activity-data', 'data'),
    State('activity-stats', 'data'),
    State('upload-data', 'fname'),
    prevent_initial_call=True
  )
  def save_activity(n_clicks, record_data, activity_data, fname):
    """Create a database record and save data files. (WIP)."""
    if (
      n_clicks is None
      or n_clicks == 0
      or record_data is None
      or activity_data is None
      or fname is None
    ):
      raise PreventUpdate

    # gotta figure this out still.
    fname_orig = f'{fname}'
    with open(fname_orig, 'w') as outfile:
      pass

    # Save the processed DataFrame as CSV
    # TODO: Extract just the filename (no path, no extension)
    fname_csv = 'tmp.csv'
    df = pd.DataFrame.from_records(record_data)
    df.to_csv(fname_csv)

    # Create a new activity record in the database (WIP)
    # This requires populating the activity-stats store with stats
    # from the file, which I don't yet have a parser for.
    # from application.models import db, Activity
    # new_act = Activity(
    #   title='Run',  # gpxreader.get_tracks()[0].name
    #   # description=activity_data['description'],
    #   created=datetime.datetime.utcnow(),
    #   # recorded=gpxreader.start_time,  # UTC
    #   # recorded=tcxreader.start_time,  # UTC
    #   # recorded=fitfilereader.{???},

    #   tz_local='US/Denver',  # is this in any of the filetypes?
      
    #   # For now, I think moving time should be the sum of the
    #   # lap times.
    #   # moving_time_s=gpxreader.lap_time_s,
    #   # moving_time_s=tcxreader.lap_time_s,
    #   # moving_time_s=fitfilereader.{???},

    #   # For now, just calculate elapsed time as the difference
    #   # between the first and last record timestamps.
    #   # elapsed_time_s=gpxreader.total_time_s,
    #   # elapsed_time_s=tcxreader.total_time_s,
    #   # elapsed_time_s=fitfilereader.{???},

    #   filepath_orig=fname_orig,
    #   filepath_csv=fname_csv,
    #   # Fields below here not required
    #   # strava_id=activity_data['id'],
    #   distance_m=activity_data['distance'],
    #   elevation_m=activity_data['total_elevation_gain'],
    #   # intensity_factor=0.85, # later
    # )
    # db.session.add(new_act)  # Adds new Activity record to database
    # db.session.commit()  # Commits all changes

  @app.callback(
    Output('file-stats', 'children'),
    # Input('activity-stats', 'data'),
    Input('upload-data', 'filename'),
    State('upload-data', 'last_modified'),
  )
  def update_file_info(fname, date):
    stats = html.Div([
      html.H5(fname),
      html.H6(datetime.datetime.fromtimestamp(date)),
      html.Hr(),
    ])

    return stats

  dashboard_activity.init_figure_callbacks(app)
  dashboard_activity.init_stats_callbacks(app)


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
    from application.converters import from_tcx
    return converters.from_tcx(io.BytesIO(decoded))

  elif filename.lower().endswith('gpx'):
    from application.converters import from_gpx
    return converters.from_gpx(io.BytesIO(decoded))


# WIP!!
UPLOAD_DIRECTORY = 'application/app_uploaded_files'

def save_file(name, content):
  """Decode and store a file uploaded with Plotly Dash.
  
  Will require some tinkering.

  Source:
  https://docs.faculty.ai/user-guide/apps/examples/dash_file_upload_download.html

  """
  data = content.encode('utf8').split(b';base64,')[1]
  with open(os.path.join(UPLOAD_DIRECTORY, name), 'wb') as fp:
    fp.write(base64.decodebytes(data))


# Uncomment this to turn on advanced stuff (overriding functions in
# this file).
# from application.plotlydash.dashboard_upload_next import init_callbacks

# from application.plotlydash.dashboard_upload_next import init_hover_callbacks, parse_contents
# from application.plotlydash.dashboard_activity_next import init_hover_callbacks, create_rows


if __name__ == '__main__':
    app.run_server(debug=True)