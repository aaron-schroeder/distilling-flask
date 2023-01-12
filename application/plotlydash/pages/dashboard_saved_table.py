import dash
from dash import dash_table, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

from application import tasks, util
from application.models import db, Activity, StravaAccount
from application.plotlydash.layout import COLORS
from application.plotlydash.util import layout_login_required


dash.register_page(__name__, path_template='/saved-list',
  title='Saved Activity List', name='Saved Activity List')


PAGE_SIZE = 25


@layout_login_required
def layout(**url_queries):

  style_data_conditional = [
    {
      'if': {'row_index': 'odd'},
      'opacity': '0.8',
    }
  ]
  style_data_conditional.extend([
    {
      'if': {'filter_query': f'{{_strava_acct_id}} = {strava_acct.strava_id}'},
      'backgroundColor': COLORS['USERS'][i]
    }
    for i, strava_acct in enumerate(StravaAccount.query.all()) 
  ])

  out = dbc.Container(
    [
      html.H2('Your Saved Activities'),
      dash_table.DataTable(
        id='datatable-saved',
        cell_selectable=False,
        page_current=0,
        page_size=int(url_queries.get('limit', PAGE_SIZE)),
        page_action='custom',
        sort_action='custom',
        # sort_mode='multi',
        # filter_action='custom',
        # filter_query='',
        style_table={'overflowX': 'auto'},
        css=[dict(selector= 'p', rule= 'margin: 0')],
        style_cell={
          'textAlign': 'right',
          'padding-right': '30px', 
        },
        style_cell_conditional=[{
          'if': {'column_id': ['Sport', 'Date', 'Title']},
          'textAlign': 'left'
        }],
        style_data={
          'whiteSpace': 'normal',
          'height': 'auto',
        },
        style_data_conditional=style_data_conditional,
        style_as_list_view=True,
        markdown_options={'link_target': '_self'}
      )
    ],
    id='dash-container',
    fluid=True,
  )

  return out


@dash.callback(
  Output('datatable-saved', 'columns'),
  Output('datatable-saved', 'data'),
  Output('datatable-saved', 'page_count'),
  Input('datatable-saved', 'page_current'),
  Input('datatable-saved', 'page_size'),
  Input('datatable-saved', 'sort_by'),
)
def update_table(page_current, page_size, sort_by):

  column_map = {
    'Sport': None,
    'TSS': Activity.tss,
    'Date': Activity.recorded,
    'Title': Activity.title,
    'Time': Activity.elapsed_time_s,
    'Distance': Activity.distance_m,
    'Elevation': Activity.elevation_m
  }

  order_by_args = []

  if sort_by and len(sort_by):
    # Sort is applied
    order_by_col = column_map.get(sort_by[0]['column_id'])
    direction = sort_by[0]['direction']

    if order_by_col is None:
      pass
    elif direction == 'asc':
      order_by_args.append(order_by_col.asc())
    else:  # desc
      order_by_args.append(order_by_col.desc())

  order_by_args.append(Activity.recorded.desc())

  page = db.paginate(
    db.select(Activity).order_by(*order_by_args),
    page=page_current + 1,
    per_page=page_size
  )
  
  dfs = pd.DataFrame([
    {
      'Sport': 'Run*',
      'Date': activity.recorded,
      'Title': f'[{activity.title}]({activity.relative_url})',
      'Time': f'{util.seconds_to_string(activity.moving_time_s, show_hour=True)}',
      'Distance': activity.distance_m,
      'Elevation': activity.elevation_m,
      'TSS': activity.tss,
      '_internal_id': activity.id,
      '_strava_acct_id': activity.strava_acct_id,
      # 'Overlap': str(Activity.find_overlap_ids(
      #   activity.start_date,
      #   activity.start_date + activity.elapsed_time,
      # ))
    }
    for activity in page
  ])

  dfs['Distance'] = dfs['Distance'].apply(lambda meters: f'{meters/util.M_PER_MI:.2f} mi')
  dfs['Elevation'] = dfs['Elevation'].apply(lambda meters: f'{meters*util.FT_PER_M:.0f} ft')
  dfs['TSS'] = dfs['TSS'].apply(lambda tss: f'{tss:.1f}')
  # eg "Sat, 12/31/2022 20:10:00"
  dfs['Date'] = dfs['Date'].dt.strftime(date_format='%a, %m/%d/%Y %H:%M:%S')

  return (
    [
      {'name': c, 'id': c, 'presentation': 'markdown'} if c == 'Title'
      else {'name': c, 'id': c}
      for c in dfs.columns
      if c not in ['_internal_id', '_strava_acct_id']
    ],
    dfs.to_dict('records'),
    page.pages
  )
