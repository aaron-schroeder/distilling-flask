import datetime
import json
import math
import os

import dash
from dash import dcc, html, callback, Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dateutil import tz
import numpy as np
import pandas as pd
import plotly.graph_objs as go

from application import util
from application.models import db, Activity
from application.plotlydash.layout import COLORS


dash.register_page(__name__, path_template='/',
  title='Training Log Dashboard', name='Training Log Dashboard')


def layout():
  # Load dates and TSS from db in to DF.
  activities=Activity.query.all()

  if len(activities) == 0:
    return dbc.Container(
      [
        html.H1('Training Log'),
        html.Hr(),
        html.Div('No activities have been saved yet.')
      ]
    )

  fields = ['recorded', 'tss', 'title', 'elapsed_time_s', 'strava_acct_id']
  df = pd.DataFrame(
    [[getattr(a, field) for field in fields] for a in activities], 
    columns=fields
  )

  df = df.sort_values(by='recorded', axis=0)

  # For now, convert to my tz - suggests setting TZ by user,
  # not by activity.
  df['recorded'] = df['recorded'].dt.tz_localize(tz.tzutc()).dt.tz_convert(tz.gettz('America/Denver'))

  calc_ctl_atl(df)

  return dbc.Container(
    [
      html.H1('Training Log'),
      html.Hr(),
      html.H2('Training Stress'),
      html.Div(
        TssGraphAIO(df, aio_id='log'),
        style={'overflowX': 'scroll'}
      ),
      html.Hr(),
      html.H2('Weekly Log'),
      dbc.Row(
        [
          dbc.Col(
            dcc.Dropdown(
              id='bubble-dropdown',
              options=[
                {'label': x, 'value': x} for x in ['Distance', 'Time', 'Elevation', 'TSS']
              ],
              value='Distance',
              searchable=False,
              clearable=False,
              style={'font-size': '12px'}
            ),
            width=2,
          ),
          dbc.Col(
            dbc.Row(
              [
                dbc.Col(
                  day,
                  style={'text-align': 'center', 'font-size': '11px'}
                )
                for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
              ],
              # justify='around',
              # justify='center',
              className='g-0',
            ),
            align='center',
            width=10,
          )
        ],
        id='calendar-header',
        className='mb-3 pb-2 border-bottom',
        style={'position': 'sticky', 'top': 0, 'zIndex': 1, 'background-color': 'white'}
      ),
      # html.Hr(),
      # CalendarDivAIO(aio_id='log'),
      html.Div(id='calendar-rows'),
      dbc.Row(
        dbc.Button(
          'Show 3 prior weeks',
          id='add-weeks',
          color='primary',
          style={'width': 'fit-content'}
        ),
        justify='center',
        className='mb-2',
      ),
      dcc.Location(id='url'),
    ],
    id='dash-container',
    fluid=True,
  )


@callback(
  Output('calendar-rows', 'children'),
  # Input('url', 'pathname'),
  Input('add-weeks', 'n_clicks'),
  # Input('bubble-dropdown', 'value'),
  State('calendar-rows', 'children'),
)
def update_calendar(n_clicks, children):
  
  n_clicks = n_clicks or 0

  # Load dates and TSS from db in to DF.
  # TODO: Consider querying the database for dates, rather than
  # loading them all into a DataFrame.
  activities=Activity.query.all()
  
  fields = ['id', 'recorded', 'tss', 'title', 'description',
            'elapsed_time_s', 'moving_time_s', 'distance_m', 'elevation_m']
  df = pd.DataFrame(
    [[getattr(a, field) for field in fields] for a in activities], 
    columns=fields
  )
  df = df.sort_values(by='recorded', axis=0)

  # For now, convert to my tz - suggests setting TZ by user,
  # not by activity.
  df['recorded'] = df['recorded'].dt.tz_localize(tz.tzutc()).dt.tz_convert(tz.gettz('America/Denver'))
  df['weekday'] = df['recorded'].dt.weekday

  # ** Coming soon: Special calendar view for current week **

  children = children or []
  today = datetime.datetime.today().date()
  idx = today.weekday() # MON = 0, SUN = 6
  # idx = (today.weekday() + 1) % 7 # MON = 0, SUN = 6 -> SUN = 0 .. SAT = 6
  for i in range(3 * n_clicks, 3 * (n_clicks + 1)):
    ix = idx + 7 * (i - 1)
    mon_latest = today - datetime.timedelta(ix) # 0-6 days ago
    mon_last = today - datetime.timedelta(ix+7) # 1+ weeks ago

    df_week = df[
      (df['recorded'].dt.date < mon_latest)
      & (df['recorded'].dt.date >= mon_last)
    ]

    children.append(dbc.Row([
      dbc.Col(
        children=create_week_sum(df_week, mon_last),
        id=f'week-summary-{i}',
        width=2,
      ),
      dbc.Col(
        # Eventually this will be just one part of one row.
        dcc.Graph(
          # id=f'week-cal-{i}',
          id={'type': 'week-cal', 'index': i},
          figure=create_week_cal(df_week),
          config=dict(displayModeBar=False),
        ),
        width=10,
      )
    ]))

  return children


@callback(
  Output({'type': 'week-cal', 'index': ALL}, 'figure'),
  # Input('url', 'pathname'),
  Input('bubble-dropdown', 'value'),
  # Input('bubble-dropdown', 'value'),
  State({'type': 'week-cal', 'index': ALL}, 'figure'),
  # if I do this, adding rows does not work right if not using distance:
  # prevent_initial_call=True,
)
def update_calendar(bubble_type, figures):

  figures = [update_week_cal(figure, bubble_type) for figure in figures]

  return figures


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


def create_week_sum(df_week, date_start):
  date_end = date_start + datetime.timedelta(6)

  if date_start.month != date_end.month:
    date_str = f'{date_start.strftime("%b %-d")}-{date_end.strftime("%b %-d")}'
  else:
    date_str = f'{date_start.strftime("%b %-d")}-{date_end.strftime("%-d")}'

  moving_time_s = df_week['moving_time_s'].sum()
  if moving_time_s < 30:
    time_str = '--:--'
  # elif moving_time_s < 3600:
  else:
    hrs = math.floor(moving_time_s / 3600)
    mins = round((moving_time_s - hrs * 3600) / 60)
    time_str = f'{hrs}h{mins}m'

  div = html.Div([
    html.Div(
      date_str,
      style={
        'font-size': '11px',
        'text-transform': 'uppercase',
        'font-weight': 'bold',
      }
    ),
    html.Div(
      [
        time_str,
        html.Span(
          f'{round(df_week["elevation_m"].sum() * util.FT_PER_M)} ft',
          style={'float': 'right'}
        ),
      ],
      style={
        'text-align': 'left',
        'font-size': '12px',
        'font-color': '#666',
      }
    ),
    html.Div(
      f'{df_week["distance_m"].sum() / util.M_PER_MI:.1f} mi',
      style={
        'font-size': '31px',
        'margin-top': '10px',
        'font-weight': 300,
      }
    ),
    html.Hr(),
  ])

  return div

def create_week_cal(df_week):
  """Create weekly training log view as a bubble chart."""
  fig = go.Figure(layout=dict(
    xaxis=dict(
      range=[-0.5, 6.5],
      showticklabels=False,
      showgrid=False,
      zeroline=False,
      fixedrange=True,
    ),
    yaxis=dict(
      range=[0, 3],
      showticklabels=False,
      showgrid=False,
      zeroline=False,
      fixedrange=True,
    ),
    margin=dict(b=0,t=0,r=0,l=0),
    height=160,
    # hoverdistance=100,
    plot_bgcolor='rgba(0,0,0,0)',
  ))

  line = dict(
    dash='dot',
    width=1,
    color='#bbb',
  )

  fig.add_hline(
    y=1, 
    layer='below',
    line=line,
  )

  for x in range(7):
    fig.add_shape(type='line', y0=1, y1=1.9, x0=x, x1=x, layer='below', line=line)
    if x not in df_week['weekday'].values:
      fig.add_annotation(
        x=x,
        y=2,
        text='Rest',
        showarrow=False,
        font=dict(
          color='#bbb',
          size=11,
          # weight=200,
        )
      )

  fig.add_trace(dict(
    x=df_week['weekday'],
    y=[2 for d in df_week['weekday']],
    text=[f'<a href="/saved/{id}">{d / util.M_PER_MI:.1f}</a>' for id, d in zip(df_week['id'], df_week['distance_m'])],
    name='easy', # they are all easy right now
    mode='markers+text',
    marker=dict(
      # size=100, # debugging
      size=df_week['distance_m'],
      # Make marker_size=100 at marathon length.
      sizemode='area',
      sizeref=(1609.34*26.2)/(0.5*100**2),
      # sizemode='diameter',
      # sizeref=(1609.34*26.2)/100,
      color='#D5E5D3',
      line_color='#BDD6BA',
      line_width=1,
      opacity=1.0,
    ),
    textposition='middle center',
    customdata=np.transpose(np.array([
      df_week['recorded'].dt.strftime('%a, %b %-d, %Y %-I:%M %p'),
      df_week['id'],
      df_week['title'], 
      df_week['description'].astype(str).str.slice(0, 50) + ' ...',
      df_week['distance_m'] / util.M_PER_MI,
      df_week['moving_time_s'].apply(util.seconds_to_string),
      (df_week['distance_m'] / df_week['moving_time_s']).apply(util.speed_to_pace),
      (df_week['distance_m'] / df_week['elapsed_time_s']).apply(util.speed_to_pace),
      df_week['elevation_m'] * util.FT_PER_M,
      df_week['tss'],
    ])),
    hovertemplate=
      '<span style="font-size:11px; color: #6D6D78">'+
      '%{customdata[0]}</span><br>'+ 
      '<span style="font-size: 16px;">%{customdata[2]}</span><br>'+ 
      '<span style="font-size: 14px; color: #6D6D78;">'+
      '%{customdata[3]}</span><br>'+
      '<b>'+
      'Distance: %{customdata[4]:.1f} mi<br>'+
      'Moving Time: %{customdata[5]}<br>'+
      'Moving Pace: %{customdata[6]}/mi<br>'+
      'Overall Pace: %{customdata[7]}/mi<br>'+
      'Elevation: %{customdata[8]:.0f} ft<br>'+
      'Training Stress: %{customdata[9]:.0f}<br>'+
      '</b>',
    hoverlabel=dict(bgcolor='#fff'),
  ))

  return fig


def update_week_cal(fig, bubble_type):
  fig = go.Figure(fig)
  
  hrefs = [f"{txt.split('>')[0]}>" for txt in fig.data[0].text]

  if bubble_type == 'Time':
    time_strs = [cdata[5] for cdata in fig.data[0].customdata]
    secs = [util.string_to_seconds(t) for t in time_strs]

    fig.data[0].text = [f'{a}{math.floor(s/3600)}hr{round((s % 3600) / 60)}m</a>' for a, s in zip(hrefs, secs)]
    
    # Convert str to seconds, and size/sizeref based on that
    fig.data[0].marker['size'] = secs
    fig.data[0].marker['sizeref'] = 3.5 * 3600 / (0.5 * 100 ** 2)
    
  elif bubble_type == 'Distance':
    dists_mi = [float(cdata[4]) for cdata in fig.data[0].customdata]

    fig.data[0].text = [f'{a}{d:.1f}</a>' for a, d in zip(hrefs, dists_mi)]

    # Need to rescale based on miles rather than meters
    fig.data[0].marker['size'] = dists_mi
    fig.data[0].marker['sizeref'] = 26.2 / (0.5 * 100 ** 2)

  elif bubble_type == 'Elevation':
    elevs_ft = [float(cdata[8]) for cdata in fig.data[0].customdata]

    fig.data[0].text = [f'{a}{e:.0f}</a>' for a, e in zip(hrefs, elevs_ft)]

    fig.data[0].marker['size'] = elevs_ft
    fig.data[0].marker['sizeref'] = 7000 / (0.5 * 100 ** 2)

  elif bubble_type == 'TSS':
    tsss = [float(cdata[9]) for cdata in fig.data[0].customdata]

    fig.data[0].text = [f'{a}{tss:.1f}</a>' for a, tss in zip(hrefs, tsss)]

    fig.data[0].marker['size'] = tsss
    fig.data[0].marker['sizeref'] = 250 / (0.5 * 100 ** 2)

  fig.update_layout(transition_duration=1000)

  return fig