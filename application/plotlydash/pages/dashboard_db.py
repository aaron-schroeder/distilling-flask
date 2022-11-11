import datetime
import json
import math
import os

import dash
from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dateutil
import pandas as pd
import plotly.graph_objs as go

from application import converters, stravatalk, util
from application.models import db, Activity
from application.plotlydash import dashboard_activity
# calc_power, create_rows, init_hover_callbacks


# dash.register_page(__name__, path_template='/saved/<activity_id>')


def layout(activity_id=None):
  if activity_id is None:
    return html.Div([])

  activity = Activity.query.get(activity_id)
  
  df = pd.read_csv(activity.filepath_csv)

  activity_dict = {
    k: f if not isinstance(f, datetime.date) else f.isoformat()
    for k, f in activity.__dict__.items() if not k.startswith('_')
  }

  # Initialize an empty layout to be populated with callback data.
  # TODO: Bring this part of layout in here? Plotter can fill it...
  # app.layout = LAYOUT
  return dbc.Container(
    [
      html.Div(id='model-stats'),
      dashboard_activity.create_stats_div(df),
      html.Div(dashboard_activity.create_plot_opts(df)),
      html.Div(id='figures'),
      dcc.Store(id='activity-data', data=df.to_dict('records')), # dataframe
      dcc.Store(id='activity-stats', data=activity_dict), # could be strava response etc
      dcc.Store(id='activity-streams')
    ],
    id='dash-container',
    fluid=True,
  )


# @callback(
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

@callback(
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

# Can't add callbacks due to component namespace issues,
# since this dashboard is now part of the same app as the strava dashboard
# and the two share components.
# TODO: Solve this with all-in-one components.
# dashboard_activity.init_figure_callbacks()
# dashboard_activity.init_stats_callbacks()
