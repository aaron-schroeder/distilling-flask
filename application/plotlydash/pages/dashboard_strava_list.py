import dash
from dash import dash_table, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

from application import tasks, util
from application.models import Activity, StravaAccount
from application.plotlydash.util import layout_login_required


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
          dbc.Label('Which activities to keep in the case of overlap?'),
          dbc.RadioItems(
            id='overlap-choice',
            options=[
              {'label': 'Existing', 'value': 'existing'},
              {'label': 'Incoming', 'value': 'incoming'},
              {'label': 'Both', 'value': 'both', 'disabled': True}
            ],
            value='existing',
            inline=True
          ),
          dbc.Checklist(
            id='save-options',
            options=[
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
            value=['add-walks'],
          ),
          dbc.Button(
            'Save All Strava Activities',
            id='save-all',
            type='submit',
            class_name='me-2',
            disabled=True,
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
        page_current=int(url_queries.get('page', 1))-1,
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
          {
            'if': {
              'filter_query': '{Saved} = "True"',
            },
            'backgroundColor': 'gray',
          },
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
      'Id': activity.id,
      'Overlap': str(Activity.find_overlap_ids(
        activity.start_date,
        activity.start_date + activity.elapsed_time,
      ))
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
    ],
    dfs.to_dict('records')
  )


@dash.callback(
  Output('url', 'href'),
  Input('save-selected', 'n_clicks'),
  Input('save-all', 'n_clicks'),
  State('strava-id', 'data'),
  State('datatable-activity', 'data'),
  State('datatable-activity', 'selected_rows'),
  State('overlap-choice', 'value')
)
def save_strava_activities(
  n_clicks_selected,
  n_clicks_all, 
  strava_account_id,
  activity_data,
  selected_rows,
  overlap_choice
):
  if (
    (not n_clicks_all and not n_clicks_selected)
    or activity_data is None
  ):
    raise PreventUpdate

  # Flash a message before/during/after redirecting like:
  # flash('Activities will be added in the background.')
  if n_clicks_all:
    client = StravaAccount.query.get(strava_account_id).client
    strava_ids = [activity.id for activity in client.get_activities()]
  elif n_clicks_selected:
    df = pd.DataFrame.from_records(activity_data)
    strava_ids = df.iloc[selected_rows, :]['Id'].to_list()

  for strava_activity_id in strava_ids:
    tasks.async_save_strava_activity.delay(
      strava_account_id,
      strava_activity_id,
      handle_overlap=overlap_choice
    )

  return '/strava/manage'
