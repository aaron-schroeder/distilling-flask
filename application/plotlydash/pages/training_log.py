import datetime
import math

import dash
from dash import dcc, html, callback, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go

from application.models import Activity
from application.util import units


dash.register_page(__name__, path_template='/',
  title='Training Log Dashboard', name='Training Log Dashboard')


def layout(**_):
  return dbc.Container(
    [
      html.H1('Week-by-Week Training Log'),
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
    ],
    id='dash-container',
    fluid=True,
  )


@callback(
  Output('calendar-rows', 'children'),
  Input('add-weeks', 'n_clicks'),
  State('calendar-rows', 'children'),
)
def update_calendar(n_clicks, children):
  
  n_clicks = n_clicks or 0

  # Load dates and TSS from db into DF.
  # TODO: Consider querying the database for dates, rather than
  # loading them all into a DataFrame.
  df = Activity.load_summary_df()

  if len(df) == 0:
    return html.Div('No activities have been saved yet.')
  
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
          figure=TrainingWeekFigure.from_dataframe(df_week),
          config=dict(displayModeBar=False),
        ),
        width=10,
      )
    ]))

  return children


@callback(
  Output({'type': 'week-cal', 'index': ALL}, 'figure'),
  Input('bubble-dropdown', 'value'),
  State({'type': 'week-cal', 'index': ALL}, 'figure'),
  # if I do this, adding rows does not work right when not using distance:
  # prevent_initial_call=True,
)
def update_calendar(bubble_type, figures):

  return [
    TrainingWeekFigure(figure, bubble_type=bubble_type)
    for figure in figures
  ]


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
          f'{round(df_week["elevation_m"].sum() * units.FT_PER_M)} ft',
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
      f'{df_week["distance_m"].sum() / units.M_PER_MI:.1f} mi',
      style={
        'font-size': '31px',
        'margin-top': '10px',
        'font-weight': 300,
      }
    ),
    html.Hr(),
  ])

  return div


class TrainingWeekFigure(go.Figure):

  # The denominator of the sizeref property, set so the marker_size
  # will be 100 when the trace value equals the sizeref numerator.
  _sizeref_denominator = 0.5 * 100 ** 2

  def __init__(self, *args, bubble_type=None, **kwargs):
    """Create weekly training log view as a bubble chart."""
    super().__init__(*args, **kwargs)

    if bubble_type:
      self._update_bubble_type(bubble_type)

  @property
  def circle_trace(self):
    return self.data[0]

  def _update_bubble_type(self, bubble_type):

    hrefs = [f"{txt.split('>')[0]}>" for txt in self.circle_trace.text]

    if bubble_type == 'Time':
      time_strs = [cdata[5] for cdata in self.circle_trace.customdata]
      secs = [units.string_to_seconds(t) for t in time_strs]

      self.circle_trace.text = [f'{a}{math.floor(s/3600)}hr{round((s % 3600) / 60)}m</a>' for a, s in zip(hrefs, secs)]
      
      # Convert str to seconds, and size/sizeref based on that
      self.circle_trace.marker['size'] = secs
      self.circle_trace.marker['sizeref'] = 3.5 * 3600 / self._sizeref_denominator
      
    elif bubble_type == 'Distance':
      dists_mi = [float(cdata[4]) for cdata in self.circle_trace.customdata]

      self.circle_trace.text = [f'{a}{d:.1f}</a>' for a, d in zip(hrefs, dists_mi)]

      # Need to rescale based on miles rather than meters
      self.circle_trace.marker['size'] = dists_mi
      self.circle_trace.marker['sizeref'] = 26.2 / self._sizeref_denominator

    elif bubble_type == 'Elevation':
      elevs_ft = [float(cdata[8]) for cdata in self.circle_trace.customdata]

      self.circle_trace.text = [f'{a}{e:.0f}</a>' for a, e in zip(hrefs, elevs_ft)]

      self.circle_trace.marker['size'] = elevs_ft
      self.circle_trace.marker['sizeref'] = 7000 / self._sizeref_denominator

    elif bubble_type == 'TSS':
      tsss = [float(cdata[9]) for cdata in self.circle_trace.customdata]

      self.circle_trace.text = [f'{a}{tss:.1f}</a>' for a, tss in zip(hrefs, tsss)]

      self.circle_trace.marker['size'] = tsss
      self.circle_trace.marker['sizeref'] = 250 / self._sizeref_denominator

    self.update_layout(transition_duration=1000)

  @classmethod
  def from_dataframe(cls, df_week):
    fig = cls(
      layout=dict(
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
        dragmode=False
      )
    )

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
      x=df_week['weekday'],  # ADS here
      y=[2 for d in df_week['weekday']],
      text=[f'<a href="/saved/{id}">{d / units.M_PER_MI:.1f}</a>' for id, d in zip(df_week['id'], df_week['distance_m'])],
      name='easy', # they are all easy right now
      mode='markers+text',
      marker=dict(
        # size=100, # debugging
        size=df_week['distance_m'],
        # Make marker_size=100 at marathon length.
        sizemode='area',
        sizeref=(1609.34*26.2) / cls._sizeref_denominator,
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
        df_week['distance_m'] / units.M_PER_MI,
        df_week['moving_time_s'].apply(units.seconds_to_string),
        (df_week['distance_m'] / df_week['moving_time_s']).apply(units.speed_to_pace),
        (df_week['distance_m'] / df_week['elapsed_time_s']).apply(units.speed_to_pace),
        df_week['elevation_m'] * units.FT_PER_M,
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
