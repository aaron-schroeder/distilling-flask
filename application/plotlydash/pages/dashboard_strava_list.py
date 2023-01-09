import math

import dash
from dash import dash_table, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

from application import util
from application.models import StravaAccount
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
      # TODO: batch-save formgroup
      dash_table.DataTable(
        id='datatable-activity',
        row_selectable='multi',
        page_current=0,
        page_size=PAGE_SIZE,
        # page_count=math.ceiling(1019/PAGE_SIZE),
        page_action='custom',
        # filter_action='custom',
        # sort_action='custom',
        # sort_mode='multi',
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
  State('strava-id', 'data'),
)
def update_table(page_current, page_size, strava_id):
  if strava_id is None:
    raise PreventUpdate
  
  strava_acct = StravaAccount.query.get(strava_id)
  activities = strava_acct.client.get_activities(limit=page_size)
  activities.per_page = page_size
  activities._page = page_current + 1

  saved_activity_id_list = [a.strava_id for a in strava_acct.activities.all()]

  df = pd.DataFrame([
    {
      'Sport': activity.type,
      'Date': activity.start_date_local,
      'Title': f'[{activity.name}](/strava/activity/{activity.id}?id={strava_acct.strava_id})',
      'Time': f'{util.seconds_to_string(activity.moving_time.total_seconds(), show_hour=True)}',
      'Distance': f'{activity.distance.to("mile").magnitude:.2f} mi',
      'Elevation': f'{activity.total_elevation_gain.to("foot").magnitude:.0f} ft',
      'Saved': activity.id in saved_activity_id_list,
      # 'Map': activity.map,  # stravalib.model.Map
    }
    for activity in activities
  ])

  return (
    [
      {'name': c, 'id': c, 'presentation': 'markdown'} if c == 'Title'
      else {'name': c, 'id': c}
      for c in df.columns
    ],
    df.to_dict('records')
  )
