import datetime

import dash
from dash import dash_table, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dateutil
import pandas as pd
from scipy.interpolate import interp1d
from sqlalchemy.exc import IntegrityError

from application import converters, util
from application.models import db, Activity, StravaAccount
from application.plotlydash.dashboard_activity import calc_power
from application.plotlydash.util import layout_login_required
import power.util as putil


dash.register_page(__name__, path_template='/strava/activities',
  title='Strava Activity List', name='Strava Activity List')


PAGE_SIZE = 25


@layout_login_required
def layout(**url_queries):

  strava_id = url_queries.get('id')

  if StravaAccount.query.get(strava_id) is None:
    return html.Div([])  # todo: add help text
    # return redirect(url_for('strava_api.authorize'))

  out = dbc.Container(
    [
      dcc.Location(id='url'),
      html.H2('Your Strava Activities'),
      dbc.Form(
        [
          dbc.Checklist(
            id='save-options',
            options=[
              {
                'label': 'Add strava activities whose times overlap with saved activities?',
                'value': 'add-overlap',
                'disabled': True,
              },
              {
                'label': 'Save walks and hikes as runs?',
                'value': 'add-walks',
                'disabled': True,
              },
              {
                'label': 'Add bike rides?',
                'value': 'add-rides',
                'disabled': True,
              },
            ],
            value=['add-overlap', 'add-walks'],
          ),
          dbc.Button(
            'Save All Strava Activities',
            id='save-all',
            type='submit',
            class_name='me-2'
          ),
          dbc.Button(
            'Save Selected Strava Activities',
            id='save-selected',
            type='submit'
          ),
        ],
        class_name='my-4'
      ),
      dash_table.DataTable(
        id='datatable-activity',
        row_selectable='multi',
        cell_selectable=False,
        page_current=0,
        page_size=int(url_queries.get('limit', PAGE_SIZE)),
        # page_count=math.ceiling(activity_count/page_size),
        page_action='custom',
        # filter_action='custom',
        # filter_query='',
        sort_action='custom',
        # sort_mode='multi',
        style_table={
          'overflowX': 'auto'
        },
        css=[dict(selector= 'p', rule= 'margin: 0')],
        style_cell={
          'textAlign': 'right',
          'padding-right': '30px', 
        },
        style_cell_conditional=[
          {
            'if': {'column_id': ['Sport', 'Date', 'Title']},
            'textAlign': 'left'
          },
        ],
        style_data={
          'whiteSpace': 'normal',
          'height': 'auto',
        },
        style_data_conditional=[
          {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(220, 220, 220)',
          },
          # {
          #   'if': {
          #     'filter_query': '{Saved} = "True"',
          #   },
          #   'backgroundColor': 'gray',
          # },
        ],
        style_as_list_view=True,
        markdown_options={'link_target': '_self'}
      ),
      dcc.Store(id='strava-id', data=strava_id)
    ],
    id='dash-container',
    fluid=True,
  )

  return out


@dash.callback(
  Output('datatable-activity', 'columns'),
  Output('datatable-activity', 'data'),
  Input('datatable-activity', 'page_current'),
  Input('datatable-activity', 'page_size'),
  Input('datatable-activity', 'sort_by'),
  State('strava-id', 'data'),
)
def update_table(page_current, page_size, sort_by, strava_id):
  if strava_id is None:
    raise PreventUpdate
  
  strava_acct = StravaAccount.query.get(strava_id)
  
  activities = strava_acct.client.get_activities(limit=page_size)
  activities.per_page = min(page_size, 200)
  activities._page = page_current + 1

  saved_activity_id_list = [a.strava_id for a in strava_acct.activities.all()]

  df = pd.DataFrame([
    {
      'Sport': activity.type,
      'Date': activity.start_date_local,
      'Title': f'[{activity.name}](/strava/activity/{activity.id}?id={strava_acct.strava_id})',
      'Time': f'{util.seconds_to_string(activity.moving_time.total_seconds(), show_hour=True)}',
      'Distance': activity.distance.to("mile").magnitude,
      'Elevation': activity.total_elevation_gain.to("foot").magnitude,
      'Saved': str(activity.id in saved_activity_id_list),
      'Id': activity.id
      # 'Map': activity.map,  # stravalib.model.Map
    }
    for activity in activities
  ])

  if sort_by and len(sort_by):
    # Sort is applied
    dfs = df.sort_values(
      sort_by[0]['column_id'],
      ascending=sort_by[0]['direction'] == 'asc'
    )
  else:
    # No sort is applied
    dfs = df

  dfs['Distance'] = dfs['Distance'].apply(lambda float: f'{float:.2f} mi')
  dfs['Elevation'] = dfs['Elevation'].apply(lambda float: f'{float:.0f} ft')
  # eg "Sat, 12/31/2022 20:10:00"
  dfs['Date'] = dfs['Date'].dt.strftime(date_format='%a, %m/%d/%Y %H:%M:%S')

  return (
    [
      {'name': c, 'id': c, 'presentation': 'markdown'} if c == 'Title'
      else {'name': c, 'id': c}
      for c in dfs.columns
      if c not in ['Id', 'Saved']
      # if c not in ['Id']
    ],
    dfs.to_dict('records')
  )


@dash.callback(
  Output('url', 'href'),
  Input('save-selected', 'n_clicks'),
  Input('save-all', 'n_clicks'),
  State('strava-id', 'data'),
  State('datatable-activity', 'data'),
  State('datatable-activity', 'selected_rows')
)
def save_strava_activities(n_clicks_selected, n_clicks_all, strava_id, activity_data, selected_rows):
  if (
    (not n_clicks_all and not n_clicks_selected)
    or activity_data is None
  ):
    raise PreventUpdate
  
  strava_acct = StravaAccount.query.get(strava_id)
  client = strava_acct.client

  # Flash a message before/during/after redirecting like:
  # flash('Activities will be added in the background.')
  if n_clicks_all:
    strava_ids='all'
  elif n_clicks_selected:
    df = pd.DataFrame.from_records(activity_data)
    strava_ids = df.iloc[selected_rows, :]['Id'].to_list()

  save_strava_activities_in_background(client, ids=strava_ids)

  return '/strava/manage'


def save_strava_activities_in_background(client, ids=[]):

  if ids == 'all':
    # Get all activity ids (assumes everything is a valid run rn)
    ids = [activity.id for activity in client.get_activities()]
  print(f'Num. of activities retrieved: {len(ids)}')

  return

  # Get data for each activity and create an entry in db.
  activities = []
  for activity_id in ids:
    df = converters.from_strava_streams(client.get_activity_streams(
      activity_id,
      types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
          'heartrate', 'cadence', 'watts', 'temp', 'moving',
          'grade_smooth']
    ))
    calc_power(df)

    if 'NGP' in df.columns:
      # Resample the NGP stream at 1 sec intervals
      # TODO: Figure out how/where to make this repeatable.
      # 1sec even samples make the math so much easier.
      interp_fn = interp1d(df['time'], df['NGP'], kind='linear')
      ngp_1sec = interp_fn([i for i in range(df['time'].max())])

      # Apply a 30-sec rolling average.
      window = 30
      ngp_rolling = pd.Series(ngp_1sec).rolling(window).mean()          
      ngp_ms = putil.lactate_norm(ngp_rolling[29:])
      cp_ms = 1609.34 / (6 * 60 + 30)  # 6:30 mile
      intensity_factor = ngp_ms / cp_ms
      total_hours = (df['time'].iloc[-1] - df['time'].iloc[0]) / 3600
      tss = 100.0 * total_hours * intensity_factor ** 2
    else:
      intensity_factor = None
      tss = None

    activity_data = client.get_activity(activity_id).to_dict()

    activities.append(Activity(
      title=activity_data['name'],
      description=activity_data['description'],
      created=datetime.datetime.utcnow(),  
      recorded=dateutil.parser.isoparse(activity_data['start_date']),
      tz_local=activity_data['timezone'],
      moving_time_s=activity_data['moving_time'],
      elapsed_time_s=activity_data['elapsed_time'],
      # Fields below here not required
      strava_id=activity_data['id'],
      strava_acct_id=strava_acct.strava_id,
      distance_m=activity_data['distance'],
      elevation_m=activity_data['total_elevation_gain'],
      intensity_factor=intensity_factor,
      tss=tss,
    ))

  try:
    db.session.add_all(activities)
    db.session.commit()

  except IntegrityError as e:
    print('There was an error saving the activities.')
    print(e)
