import dash
from dash import dash_table, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd

from distilling_flask.models import db, Activity, StravaAccount
from distilling_flask.plotlydash.layout import COLORS
from distilling_flask.util import units


dash.register_page(__name__, path_template='/storage-table',
  title='Local Document List', name='Local Document List')


PAGE_SIZE = 25


def layout(**url_queries):
  style_data_conditional = [
    {
      'if': {'row_index': 'odd'},
      'opacity': '0.8',
    }
  ]

  out = dbc.Container(
    [
      html.H1('Local Activity Files'),
      dash_table.DataTable(
        id='datatable-storage',
        columns=[
          {'name': 'ID', 'id': 'ID',},
          {'name': 'Path', 'id': 'loc', 'presentation': 'markdown'},
        ],
        data=[{'ID': 1, 'loc': '[/mnt/c/Users/Aaron/Dropbox/personal](#)'}],
        # page_count=1,
        cell_selectable=False,
        page_current=0,
        page_size=int(url_queries.get('limit', PAGE_SIZE)),
        page_action='custom',
        sort_action='custom',
        # sort_mode='multi',
        # filter_action='custom',
        # filter_query='',
        style_table={'overflowX': 'auto'},
        css=[
          dict(selector='p', rule='margin: 0'),
          dict(selector='.dash-table-container '
                        '.dash-spreadsheet-container '
                        '.dash-spreadsheet-inner td:hover', 
               rule='background-color: hotpink;'),
        ],
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