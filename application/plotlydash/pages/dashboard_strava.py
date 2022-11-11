import datetime
import json
import math
import os

from dash import Dash, dash_table, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dateutil
import pandas as pd
import plotly.graph_objs as go

from application import converters, stravatalk, util
from application.plotlydash import dashboard_activity
# calc_power, create_rows, init_hover_callbacks
from application.plotlydash import layout

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')


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
    routes_pathname_prefix='/dash-activity/',    
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
  app.layout.children.insert(0, html.Div(id='strava-stats'))

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
    Output('activity-streams', 'data'),
    Input('url', 'pathname')
  )
  def get_strava_api_data(pathname):
    # Extract the activity id from the url, whatever it is.
    # eg `/whatever/whateverelse/activity_id/` -> `activity_id`
    activity_id = os.path.basename(os.path.normpath(pathname))

    stream_json = stravatalk.get_activity_streams_json(activity_id, ACCESS_TOKEN)

    activity_json = stravatalk.get_activity_json(activity_id, ACCESS_TOKEN)

    # Read the Strava json response into a DataFrame and perform
    # additional calculations on it.
    df = converters.from_strava_streams(stream_json)
    dashboard_activity.calc_power(df)

    return df.to_dict('records'), activity_json, stream_json

  @app.callback(
    Output('save-result', 'children'),
    Input('save-activity', 'n_clicks'),
    State('activity-data', 'data'),
    State('activity-streams', 'data'),
    State('activity-stats', 'data'),
    State('intensity-factor', 'value'),
    State('tss', 'value'),
    prevent_initial_call=True
  )
  def save_activity(
    n_clicks, 
    record_data, 
    stream_list, 
    activity_data, 
    intensity_factor,
    tss
  ):
    """Create database record for activity and save data files."""
    if (
      n_clicks is None
      or n_clicks == 0
      or record_data is None
      or stream_list is None
      or activity_data is None
    ):
      raise PreventUpdate

    fname_json = f'application/activity_files/original/{activity_data["id"]}.json'
    fname_csv = f'application/activity_files/csv/{activity_data["id"]}.csv'

    # Create a new activity record in the database
    from application.models import db, Activity
    from sqlalchemy.exc import IntegrityError

    try:
      new_act = Activity(
        title=activity_data['name'],
        description=activity_data['description'],
        created=datetime.datetime.utcnow(),  
        recorded=dateutil.parser.isoparse(activity_data['start_date']),
        tz_local=activity_data['timezone'],
        moving_time_s=activity_data['moving_time'],
        elapsed_time_s=activity_data['elapsed_time'],
        filepath_orig=fname_json,
        filepath_csv=fname_csv,
        # Fields below here not required
        strava_id=activity_data['id'],
        distance_m=activity_data['distance'],
        elevation_m=activity_data['total_elevation_gain'],
        intensity_factor=intensity_factor,
        tss=tss,
      )
      db.session.add(new_act)
      db.session.commit()

    except IntegrityError as e:
      print(e)
      return html.Div([
        'There was an error saving this activity.'
      ])

    # Save the strava response json
    with open(fname_json, 'w') as outfile:
      json.dump(stream_list, outfile)

    # Save the processed DataFrame as CSV
    df = pd.DataFrame.from_records(record_data)
    df.to_csv(fname_csv)

    return f'Activity saved successfully! Internal ID = {new_act.id}'

  @app.callback(
    Output('strava-stats', 'children'),
    Input('activity-stats', 'data'),
  )
  def update_stats(activity_data):
    """Fill the `stats` div with Strava summary data."""
    if activity_data is None:
      raise PreventUpdate

    children = [
      html.H2(f"{activity_data['name']} ({activity_data['start_date_local']})"),
      dbc.Row([
        # dbc.Col(f"{activity_data['distance'] / 1609.34:.2f} mi"),
        dbc.Col(f"{activity_data['elapsed_time']} sec (total)"),
        dbc.Col(f"{activity_data['total_elevation_gain'] * util.FT_PER_M:.0f} ft (gain)"),
        # dbc.Col(f"{activity_data['moving_time']} sec (moving)"),
      ]),
      html.Div(activity_data['description']),
      dbc.Row([
        dbc.Col(
          dbc.Button('Save activity to DB', id='save-activity'),
          # align='center',
          # className='text-center',
        ),
        dbc.Col(
          id='save-result',
        )
      ]),
      html.Hr(),
    ]

    #     'start_date', 'gear_id',
    #     'average_cadence', 'average_heartrate',
    #     'calories', 'device_name', 'gear', 'segment_efforts',
    #     'splits_metric', 'splits_standard', 'laps', 'best_efforts'

    return children

  dashboard_activity.init_figure_callbacks(app)
  dashboard_activity.init_stats_callbacks(app)

  @app.callback(
    Output('moving-table', 'data'),
    Output('moving-table', 'columns'),
    Input('activity-stats', 'data'),
    State('moving-table', 'data'),
  )
  def add_strava_stats_to_table(activity_data, table_records):
    df_stats = pd.DataFrame.from_records(table_records)
    # df_stats.index = df_stats['']

    strava_row = pd.Series([])
    strava_row[''] = 'Strava'
    strava_row['Distance (m)'] = activity_data['distance']
    strava_row['Time (s)'] = activity_data['moving_time']
    strava_row['Speed (m/s)'] = activity_data['average_speed']
    strava_row['Pace'] = util.speed_to_pace(activity_data['average_speed'])
    strava_row['Time'] = util.seconds_to_string(activity_data['moving_time'])
    strava_row['Distance (mi)'] = activity_data['distance'] / util.M_PER_MI
    
    df_stats = df_stats.append(strava_row, ignore_index=True)

    return (
      df_stats.to_dict('records'),
      dashboard_activity.create_moving_table_cols(df_stats.columns)
    )

