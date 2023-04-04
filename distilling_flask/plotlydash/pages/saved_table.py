import dash
from dash import dash_table, dcc, html, Input, Output, State, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaApiActivity, StravaImportStorage
from distilling_flask.plotlydash.layout import COLORS
from distilling_flask.util import units
from distilling_flask.util.feature_flags import flag_set


dash.register_page(__name__, path_template='/saved-list',
  title='Saved Activity List', name='Saved Activity List')


PAGE_SIZE = 25


def layout(**url_queries):

  style_data_conditional = [
    {
      'if': {'row_index': 'odd'},
      'opacity': '0.8',
    }
  ]
  style_data_conditional.extend([
    {
      'if': {'filter_query': f'{{import_storage_id}} = {strava_acct.id}'},
      'backgroundColor': COLORS['USERS'][i]
    }
    for i, strava_acct in enumerate(StravaImportStorage.query.all()) 
  ])

  out = dbc.Container(
    [
      html.H1('Strava API Activities'),
      dbc.Form(
        [
          dbc.Label('Which activities to keep in the case of overlap?'),
          dbc.RadioItems(
            id='overlap-choice',
            options=[
              {'label': 'Existing', 'value': 'existing'},
              {'label': 'Incoming', 'value': 'incoming', 'disabled': True},
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
              # {
              #   'label': 'Add bike rides?',
              #   'value': 'add-rides',
              #   'disabled': True,
              # },
            ],
            value=['add-walks'],
          ),
          dbc.Button(
            'Sync',
            id='save-all',
            type='submit',
            class_name='me-2',
            # disabled=True,
          ),
        ],
        class_name='my-4'
      ),

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
  Input('save-all', 'n_clicks'),
  State('overlap-choice', 'value')
)
def update_table(page_current, page_size, sort_by, n_clicks, overlap_choice):
  # if not ctx.triggered_id:
    # raise PreventUpdate

  # First, sync the db if requested.
  if ctx.triggered_id == 'save-all':
    # TODO: Display an animation or flash a message like:
    # flash('Activities will be added in the background.')
    for storage in db.session.scalars(db.select(StravaImportStorage)).all():
      storage.sync()

  order_by_args = []
  if (
    sort_by and len(sort_by)
    and (order_by_col := getattr(StravaApiActivity, sort_by[0]['column_id'], None))
    # and isinstance(order_by_col, sqlalchemy.orm.attributes.InstrumentedAttribute)
  ):
    # order_by_col = getattr(StravaApiActivity, sort_by[0]['column_id'], None)
    # order_by_col = sort_by[0]['column_id']
    # order_by_col = column_map.get(sort_by[0]['column_id'])

    # Sort is applied
    direction = sort_by[0]['direction']
    order_by_args.append(getattr(order_by_col, direction)())
  # order_by_args.append(StravaApiActivity.recorded.desc())
  order_by_args.append(StravaApiActivity.created.desc())

  page = db.paginate(
    db.select(StravaApiActivity).order_by(*order_by_args),
    page=page_current + 1,
    per_page=page_size
  )

  if page.total == 0:
    return ([], [], 0)
  
  dfs = pd.DataFrame([
    {
      'id': activity.id,
      'key': activity.key,
      'import_storage_id': activity.import_storage_id,
      # Pretty titles based on properties
      'Sport': 'Run*',
      'Date': activity.recorded,
      'Title': f'[{activity.title}]({activity.relative_url})',
      'Time': f'{units.seconds_to_string(activity.moving_time_s, show_hour=True)}',
      'Distance': activity.distance_m,
      'Elevation': activity.elevation_m,
      'TSS': activity.tss,
      # 'Saved': str(activity.id in saved_activity_id_list),
      # 'Id': activity.id,
      # 'Overlap': str(StravaApiActivity.find_overlap_ids(
      #   activity.start_date,
      #   activity.start_date + activity.elapsed_time,
      # ))
    }
    for activity in page
  ]).dropna(axis=1)

  if dfs.dtypes['Date'] == 'datetime64[ns]':
    dfs['Date'] = dfs['Date'].dt.strftime(date_format='%a, %m/%d/%Y %H:%M:%S')
  if 'Distance' in dfs.columns:
    dfs['Distance'] = dfs['Distance'].apply(lambda meters: f'{meters/units.M_PER_MI:.2f} mi')
  if 'Elevation' in dfs.columns:
    dfs['Elevation'] = dfs['Elevation'].apply(lambda meters: f'{meters*units.FT_PER_M:.0f} ft')
  if 'TSS' in dfs.columns:
    dfs['TSS'] = dfs['TSS'].apply(lambda tss: f'{tss:.1f}')
  # eg "Sat, 12/31/2022 20:10:00"

  return (
    [
      {'name': c, 'id': c, 'presentation': 'markdown'} if c == 'Title'
      else {'name': c, 'id': c}
      for c in dfs.columns
      # if c not in ['_internal_id', '_strava_acct_id']
    ],
    dfs.to_dict('records'),
    page.pages
  )
