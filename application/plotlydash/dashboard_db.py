import datetime
import json
import math
import os

from dash import Dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dateutil
import pandas as pd
import plotly.graph_objs as go

from application import converters, stravatalk, util
from application.models import db, Activity
from application.plotlydash import dashboard_activity
# calc_power, create_rows, init_hover_callbacks
from application.plotlydash import layout


def add_dashboard_to_flask(server):
  """Create a Plotly Dash dashboard with the specified server.

  This is actually used to create a dashboard that piggybacks on a
  Flask app, using that app its server.

  TODO: Consider peeling this off into its own file, or separating it
  in some way. I am just thinking about the parallels between this
  dashboard and the upload dashboard. Thinking it might make sense to
  have a file that creates the strava dashboard and adds it to a
  flask app, and a file that does the same for the upload dashboard.
  Then this file would contain the functions they had in common (likely
  all functions relating to cleaned DataFrames).
  
  """
  dash_app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash-saved-activity/',    
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
      # '/static/css/styles.css',  # Not yet.
    ],
  )

  init_layout(dash_app)

  init_callbacks(dash_app)

  return dash_app.server


def init_layout(app):
  # Initialize an empty layout to be populated with callback data.
  # TODO: Bring this part of layout in here? Plotter can fill it...
  # app.layout = LAYOUT
  app.layout = layout.init_layout()

  # Create a div to display Strava's activity summary data.
  app.layout.children.insert(0, html.Div(id='model-stats'))

  # Use the url of the dash app to retrieve and display strava data.
  # dash_app.layout.children.append(
  app.layout.children.append(
    dcc.Location(id='url', refresh=False)
  )

  app.layout.children.append(
    dcc.Store(id='activity-streams')
  )


def init_callbacks(app):
  @app.callback(
    Output('activity-data', 'data'),
    Output('activity-stats', 'data'),
    # Output('activity-streams', 'data'),
    Input('url', 'pathname')
  )
  def get_saved_file_data(pathname):
    # Extract the activity id from the url, whatever it is.
    # eg `/whatever/whateverelse/activity_id/` -> `activity_id`
    activity_id = os.path.basename(os.path.normpath(pathname))

    activity = Activity.query.get(activity_id)
    
    df = pd.read_csv(activity.filepath_csv)

    activity_dict = {
      k: f if not isinstance(f, datetime.date) else f.isoformat()
      for k, f in activity.__dict__.items() if not k.startswith('_')
    }

    return df.to_dict('records'), activity_dict

  # @app.callback(
  #   Output('save-result', 'children'),
  #   Input('save-activity', 'n_clicks'),
  #   State('activity-data', 'data'),
  #   State('activity-streams', 'data'),
  #   State('activity-stats', 'data'),
  #   State('intensity-factor', 'value'),
  #   State('tss', 'value'),
  #   prevent_initial_call=True
  # )
  # def save_activity(
  #   n_clicks, 
  #   record_data, 
  #   stream_list, 
  #   activity_data, 
  #   intensity_factor,
  #   tss
  # ):
  #   """Create database record for activity and save data files."""
  #   if (
  #     n_clicks is None
  #     or n_clicks == 0
  #     or record_data is None
  #     or stream_list is None
  #     or activity_data is None
  #   ):
  #     raise PreventUpdate

  #   fname_json = f'application/activity_files/original/{activity_data["id"]}.json'
  #   fname_csv = f'application/activity_files/csv/{activity_data["id"]}.csv'

  #   # Create a new activity record in the database
  #   from application.models import db, Activity
  #   from sqlalchemy.exc import IntegrityError

  #   try:
  #     new_act = Activity(
  #       title=activity_data['name'],
  #       description=activity_data['description'],
  #       created=datetime.datetime.utcnow(),  
  #       recorded=dateutil.parser.isoparse(activity_data['start_date']),
  #       tz_local=activity_data['timezone'],
  #       moving_time_s=activity_data['moving_time'],
  #       elapsed_time_s=activity_data['elapsed_time'],
  #       filepath_orig=fname_json,
  #       filepath_csv=fname_csv,
  #       # Fields below here not required
  #       strava_id=activity_data['id'],
  #       distance_m=activity_data['distance'],
  #       elevation_m=activity_data['total_elevation_gain'],
  #       intensity_factor=intensity_factor,
  #       tss=tss,
  #     )
  #     db.session.add(new_act)
  #     db.session.commit()

  #   except IntegrityError as e:
  #     print(e)
  #     return html.Div([
  #       'There was an error saving this activity.'
  #     ])

  #   # Save the strava response json
  #   with open(fname_json, 'w') as outfile:
  #     json.dump(stream_list, outfile)

  #   # Save the processed DataFrame as CSV
  #   df = pd.DataFrame.from_records(record_data)
  #   df.to_csv(fname_csv)

  #   return f'Activity saved successfully! Internal ID = {new_act.id}'

  @app.callback(
    Output('model-stats', 'children'),
    Input('activity-stats', 'data'),
  )
  def update_stats(activity_data):
    """Fill the div with Activity model data."""
    if activity_data is None:
      raise PreventUpdate

    children = [
      html.H2(f"{activity_data['title']} ({activity_data['recorded']})"),
      dbc.Row([
        # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
        dbc.Col(f"{activity_data['elapsed_time_s']} sec (total)"),
        dbc.Col(f"{activity_data['elevation_m'] * util.FT_PER_M:.0f} ft (gain)"),
        # dbc.Col(f"{activity_data['moving_time']} sec (moving)"),
        dbc.Col(f"{activity_data['tss']} ({activity_data['intensity_factor']})"),
      ]),
      html.Div(activity_data['description']),
      # dbc.Row([
      #   dbc.Col(
      #     dbc.Button('Save activity to DB', id='save-activity'),
      #     # align='center',
      #     # className='text-center',
      #   ),
      #   dbc.Col(
      #     id='save-result',
      #   )
      # ]),
      html.Hr(),
    ]

    return children

  dashboard_activity.init_figure_callbacks(app)
  dashboard_activity.init_stats_callbacks(app)

