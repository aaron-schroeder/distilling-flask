import datetime
import math

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go

from application.models import Activity
from application.plotlydash.layout import COLORS


dash.register_page(__name__, path_template='/stress',
  title='Training Stress Dashboard', name='Training Stress Dashboard')


def layout():
  df = Activity.load_summary_df()

  if len(df) == 0:
    return dbc.Container(
      [
        html.H1('Training Stress'),
        html.Hr(),
        html.Div('No activities have been saved yet.')
      ]
    )

  calc_ctl_atl(df)

  return dbc.Container(
    [
      html.H1('Training Stress'),
      html.Hr(),
      html.Div(
        TssGraphAIO(df, aio_id='stress'),
        style={'overflowX': 'scroll'}
      ),
    ],
    id='dash-container',
    fluid=True,
  )


def calc_ctl_atl(df):
  """Add power-related columns to the DataFrame.
  
  For more, see boulderhikes.views.ActivityListView

  """
  df.fillna({'tss': 0.0}, inplace=True)

  # atl_pre = [0.0]
  atl_0 = 0.0
  atl_pre = [atl_0]
  atl_post = [ df['tss'].iloc[0] / 7.0 + atl_0]
  
  # ctl_pre = [0.0]
  ctl_0 = 0.0
  ctl_pre = [ctl_0]
  ctl_post = [ df['tss'].iloc[0] / 42.0 + ctl_0]
  for i in range(1, len(df)):
    delta_t_days = (
      df['recorded'].iloc[i] - df['recorded'].iloc[i-1]
    ).total_seconds() / (3600 * 24)
    
    atl_pre.append(
      (atl_pre[i-1] + df['tss'].iloc[i-1] / 7.0) * (6.0 / 7.0) ** delta_t_days
    )
    atl_post.append(
      df['tss'].iloc[i] / 7.0 + atl_post[i-1] * (6.0 / 7.0)  ** delta_t_days
    )
    ctl_pre.append(
      (ctl_pre[i-1] + df['tss'].iloc[i-1] / 42.0) * (41.0 / 42.0) ** delta_t_days
    )
    ctl_post.append(
      df['tss'].iloc[i] / 42.0 + ctl_post[i-1] * (41.0 / 42.0) ** delta_t_days
    )

  df['ATL_pre'] = atl_pre
  df['CTL_pre'] = ctl_pre
  df['ATL_post'] = atl_post
  df['CTL_post'] = ctl_post


def TssGraphAIO(df, aio_id=None):
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
        range=[t_min, t_max]
      ),
      yaxis=dict(
        range=[0, 1.1 * df['tss'].max()],
        tickformat='.1f',
      ),
      margin=dict(b=40,t=0,r=0,l=0),
      legend={'orientation': 'h'}
    )
  )

  for i, (strava_id, df_id) in enumerate(df.groupby('strava_acct_id')):
    fig.add_trace(go.Scatter(
      x=df_id['recorded'], 
      y=df_id['tss'], 
      name=f'TSS ({strava_id})',
      text=df_id['title'],
      mode='markers',
      line_color=COLORS['USERS'][i],
    ))

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

  px_per_year = 800
  required_graph_px = px_per_year * (t_max - t_min).total_seconds() / datetime.timedelta(days=365).total_seconds()

  return dcc.Graph(
    id=aio_id,
    figure=fig,
    config={'displayModeBar': False},
    style={'width': f'{required_graph_px}px'},
  )
