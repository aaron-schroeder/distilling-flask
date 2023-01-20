import datetime

import dash
from dash import callback, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go

from application.models import Activity
from application.plotlydash.layout import COLORS
from application.util.dataframe import calc_ctl_atl


dash.register_page(__name__, path_template='/stress',
  title='Training Stress Dashboard', name='Training Stress Dashboard')


def layout(**_):
  df = Activity.load_summary_df()

  if len(df) == 0:
    return dbc.Container(
      [
        html.H1('Training Stress'),
        html.Hr(),
        html.Div('No activities have been saved yet.')
      ]
    )

  df_padded = calc_ctl_atl(df)

  return dbc.Container(
    [
      html.H1('Training Stress'),
      html.Hr(),
      TssGraph(df_padded, id='stress-graph'),
      dcc.Store(
        id='total-seconds',
        data=(df['recorded'].max() - df['recorded'].min()).total_seconds()
      )
    ],
    id='dash-container',
    fluid=True,
  )


def TssGraph(df, id=None):
  """"
  Args:
    df (pd.DataFrame): A DataFrame representing a time-indexed DataFrame
      containing TSS for each recorded activity.

  Returns:
    dcc.Graph: dash component containing a visualization of the
    training stress data contained in the DataFrame.
  
  """

  df_stress = pd.DataFrame.from_dict({
    'ctl': pd.concat([df['CTL_pre'], df['CTL_post']]),
    'atl': pd.concat([df['ATL_pre'], df['ATL_post']]),
    'date': pd.concat([
      df['recorded'],
      df['recorded'] + df['elapsed_time_s'].apply(pd.to_timedelta, unit='s')
    ]),
  }).sort_values(by='date', axis=0)

  t_max = df['recorded'].max()
  # t_min = max(df['recorded'].min(), df['recorded'].max() - datetime.timedelta(days=365))
  t_min = df['recorded'].min()

  fig = go.Figure(
    layout=dict(
      xaxis=dict(
        # range=[t_min, t_max],
        rangeselector=dict(
          buttons=list([
            dict(
              label='1m',
              step='month',
              count=1,
              stepmode='backward'
            ),
            dict(
              label='6m',
              step='month',
              count=6,
              stepmode='backward'
            ),
            dict(
              label='YTD',
              step='year',
              count=1,
              stepmode='todate'
            ),
            dict(
              label='1y',
              step='year',
              count=1,
              stepmode='backward'
            ),
            # dict(step='all')
          ])
        ),
        rangeslider=dict(visible=True),
        range=[t_min, t_max],
        rangeslider_range=[t_min, t_max],
        autorange=False,
      ),
      yaxis=dict(
        # range=[0, 1.1 * df['tss'].max()],
        tickformat='.1f',
      ),
      margin=dict(b=40,t=0,r=0,l=0),
      legend={
        'orientation': 'h',
        'y': 1,
        # 'yanchor': 'bottom',
        'yanchor': 'top',
        'x': 1,
        'xanchor': 'right',
      }
    )
  )

  fig.add_trace(go.Scatter(
    # x=df['recorded'],
    x=df_stress['date'],
    # y=df['CTL_post'],
    y=df_stress['ctl'],
    name='CTL',
    fill='tozeroy',
    mode='lines',
    line_color=COLORS['CTL'],
    # fillcolor='rgba(239, 85, 59, 0.5)',
  ))

  fig.add_trace(go.Scatter(
    x=df_stress['date'],
    y=df_stress['atl'],
    name='ATL',
    text=df_stress['atl']-df_stress['ctl'],
    hovertemplate='%{x}: ATL=%{y:.1f}, TSB=%{text:.1f}',
    fill='tonexty',
    mode='lines',
    line_color=COLORS['ATL'],
  ))

  # df_nondummy_tss = df.loc[~df['strava_acct_id'].isnull(), :]
  df_tss = df.loc[df['tss'] > 0, :]
  strava_id_list = [id if pd.notnull(id) else None for id in df_tss['strava_acct_id']]
  colors_by_id = {
    strava_acct_id: COLORS['USERS'][i]
    for i, strava_acct_id in enumerate(set(strava_id_list))
  }
  fig.add_trace(go.Scatter(
    x=df_tss['recorded'],
    y=df_tss['tss'], 
    name='TSS',
    text=df_tss['title'],
    customdata=df_tss['strava_acct_id'],
    mode='markers',
    marker_color=[colors_by_id[id] for id in strava_id_list],
  ))

  return dcc.Graph(
    id=id,
    figure=fig,
    config={'displayModeBar': False},
  )
