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

  df_padded = calc_ctl_atl(df)

  return dbc.Container(
    [
      html.H1('Training Stress'),
      html.Hr(),
      html.Div(
        [
          dbc.Label('Choose timescale'),
          dbc.RadioItems(
            options=[
              {'label': 'Week', 'value': 'week'},
              {'label': 'Month', 'value': 'month'},
              {'label': 'Year', 'value': 'year'},
              {'label': 'All-time', 'value': 'alltime'},
            ],
            value='month',
            id='radioitems-timescale',
            inline=True,
          ),
        ]
      ),
      html.Div(
        TssGraph(df_padded, id='stress-graph'),
        style={'overflowX': 'scroll'}
      ),
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

  return dcc.Graph(
    id=id,
    figure=fig,
    config={'displayModeBar': False},
  )


def required_graph_px(total_seconds, timescale='alltime'):
  px_per_year = {
    'alltime': 800,
    'year': 3000,
    'month': 36000,
    'week': 150000,
  }
  total_years = total_seconds / datetime.timedelta(days=365).total_seconds()
  return px_per_year.get(timescale, 2000) * total_years


@callback(
  Output('stress-graph', 'style'),
  Input('radioitems-timescale', 'value'),
  State('total-seconds', 'data')
)
def update_fig_width(timescale_choice, total_seconds):
  if (
    timescale_choice not in ('week', 'month', 'year', 'alltime') 
    or total_seconds is None
  ):
    raise PreventUpdate

  px = max(
    required_graph_px(float(total_seconds), timescale=timescale_choice), 
    120
  )

  return {'width': f'{px}px'}