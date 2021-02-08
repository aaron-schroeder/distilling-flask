import math
import json
import datetime

import plotly.graph_objs as go


def create_map_fig(df):
  """Create a map figure using mapbox's plotly package.

  Parameters
  ----------
  df (pd.DataFrame):
    Description.

  Returns
  -------
  map_fig (go.Figure):
    Description.
  """
  map_fig = go.Figure(layout=dict(height=350))
  
  map_fig.add_trace(go.Scattermapbox(
    lon=df['lon'],
    lat=df['lat'],
    customdata=df['time'],
    name='Full GPS',
    hovertemplate='%{customdata} sec<extra></extra>',
    mode='markers',
  ))
  
  map_fig.update_mapboxes(
    style='open-street-map',
    center_lat=df['lat'].mean(),
    center_lon=df['lon'].mean(),
    zoom=13,
  )

  map_fig.update_layout(margin=dict(b=0,t=0,r=0,l=0))

  return map_fig


def create_xy_plotter_figs(df):
  """Return multiple plotly figures representing a pd.DataFrame.
  
  Adapted from `create_xy_fig(df)`. This function can provide multiple
  figures, depending on what fields exist in the DataFrame. Developed
  this to keep track of the operations involved with creating multiple
  graph images in my Dash app.

  Returns:
    dict(go.Figure): Maps figure names to plotly Figure instances.

  TODO:
    * Consider that this might go into the dashboard file instead.
      This stuff is Dash-specific. However, I think I like having a
      default series of plots that emerge based on what fields are
      in the DF. I'll figure out how I want to do it.
  """
  plotter = Plotter(df, x_series_name='time')

  # *** ELEVATION TRACES ***
  # TODO: Put a check for elevation in the DF here? I only proceed 
  # safely because I know exactly how the DF is prepared.
  plotter.init_fig('elevation')

  # Update the `elevation` figure's default axis.
  plotter.figs['elevation'].update_yaxes(
    range=[
      math.floor(df['altitude'].min() / 200) * 200,
      math.ceil(df['altitude'].max() / 200) * 200
    ],
    ticksuffix=' m',
    hoverformat='.2f',
  )

  # Add trace to the `elevation` figure, on the default yaxis.
  plotter.add_trace('elevation', 'altitude', visible=True)

  # *** END OF ELEVATION TRACES ***

  # *** GRADE TRACES ***

  # Create a new yaxis for grade on the right side of the 
  # elevation plot (which has main yaxis1, or yaxis.)
  # TODO: Consider making this a Plotter method.
  plotter.figs['elevation'].update_layout(
    yaxis2=dict(
      anchor='x',
      overlaying='y',
      side='right',
      #title=dict(text='Grade (%)'),
      ticksuffix='%',
      range=[-75, 75],
      hoverformat='.2f',
      showticklabels=False,
      showgrid=False,
    
      # Turn on the zeroline and make it visible in this color scheme.
      zeroline=True,
      zerolinewidth=1, 
      zerolinecolor='black',
    )
  )

  # Add grade traces.
  # TODO: What if Plotter kept track of where each field needed to be
  # plotted? Like, elevation is y1 and grade is y2 of figure 1, but 
  # don't make the end user keep track of that.
  plotter.add_trace('elevation', 'grade_smooth', yaxis='y2', visible=True)

  # *** END OF GRADE ***

  # *** SPEED / VELOCITY ***

  # Create a figure for velocity.
  plotter.init_fig('speed')

  plotter.figs['speed'].update_yaxes(
    range=[-0.1, 6.0],
    ticksuffix=' m/s',
    hoverformat='.2f',

    # Turn on the zeroline and make it visible
    zeroline=True,
    zerolinewidth=1, 
    zerolinecolor='black',
  )

  # See min/mile (mm:ss) instead of m/s.
  # import datetime
  # import math
  def speed_to_pace(speed_ms):
    """Came over from `boulderhikes/utils.py`"""
    if speed_ms is None or math.isnan(speed_ms):
      return speed_ms
    
    if speed_ms <= 0.1:
      return '24:00:00'

    pace_min_mile = 1609.34 / (speed_ms * 60.0)
    hrs = math.floor(pace_min_mile/60.0), 
    mins = math.floor(pace_min_mile % 60),
    secs = math.floor(pace_min_mile*60.0 % 60)
    mile_pace_time = datetime.time(
      math.floor(pace_min_mile/60.0), 
      math.floor(pace_min_mile % 60),
      math.floor(pace_min_mile*60.0 % 60)
    )

    if mile_pace_time.hour > 0:
      return mile_pace_time.strftime('%H:%M:%S')
    
    return mile_pace_time.strftime('%-M:%S')

  speed_text = df['velocity_smooth'].apply(speed_to_pace)

  plotter.add_trace('speed', 'velocity_smooth', 
                    yaxis='y1', text=speed_text, visible=True)

  # *** END OF SPEED / VELOCITY ***

  # *** REMAINING FIELDS ***

  # *** HEART RATE ***
  plotter.figs['speed'].update_layout(
    yaxis2=dict(
      anchor='x',
      overlaying='y',
      side='right',
      ticksuffix=' bpm',
      range=[60, 220],
      hoverformat='.0f',
      showticklabels=False,
      showgrid=False,
    )
  )

  plotter.add_trace('speed', 'heartrate', yaxis='y2',
                    line=dict(color='#d62728'))

  # *** END OF HEART RATE ***

  # *** CADENCE ***

  plotter.figs['speed'].update_layout(
    yaxis3=dict(
      anchor='x',
      overlaying='y',
      side='right',
      ticksuffix=' spm',
      range=[60, 220],
      hoverformat='.0f',
      showticklabels=False,
      showgrid=False,
    )
  )

  plotter.add_trace('speed', 'cadence', yaxis='y3', mode='markers', marker=dict(size=2))

  # *** END OF CADENCE ***

  # *** MOVING/STOPPED ***

  # Draw rectangles on the figure corresponding to stopped periods.
  # TODO: Make this into its own function, I think.

  times_stopped = df.index.to_series().groupby(by=(df['moving']))

  # Find all the timestamps when strava switches the user from stopped
  # to moving, or from moving to stopped.
  switch_times = df['time'][df['moving'].shift(1) != df['moving']].to_list()

  rect_bounds_all = [
    (
      switch_times[i], 
      switch_times[i+1] - 1
    )
    for i in range(0, len(switch_times) - 1)
  ]

  rect_bounds_all.append((switch_times[-1], df['time'].iloc[-1]))
  
  if df['moving'][0]:
    # We start off MOVING.
    rect_bounds_off = rect_bounds_all[1::2]
  else:
    # We start off STOPPED.
    rect_bounds_off = rect_bounds_all[::2]

  shapes = [
    dict(
      type='rect',
      #layer='below',
      line={'width': 0}, 
      #fillcolor='LightSalmon',
      fillcolor='red',
      opacity=0.5,
      xref='x',
      x0=x[0],
      x1=x[1],
      yref='paper',
      y0=0,
      y1=1,)
    for x in rect_bounds_off
  ]

  #Something like this.
  plotter.figs['speed'].update_layout(dict(shapes=shapes,))

  # *** END OF MOVING/STOPPED ***

  # Return whatever figures I need from the dict (all of them).
  return plotter.figs


class Plotter(object):
  def __init__(self, df, x_series_name='time'):
    self.df = df
    #self.fig = self.init_fig()
    self.figs = {}
    self.set_x_series_name(x_series_name)

  def init_fig(self, fig_name):
    # Should I add kwargs? We will see.

    fig = go.Figure(layout=dict(height=400))
    
    fig.update_layout(dict(
      margin=dict(b=0,t=0,r=0,l=0),
      #paper_bgcolor='rgba(0,0,0,0)',
      #plot_bgcolor='rgba(0,0,0,0)',
      #legend=dict(yanchor='bottom', y=0.01),
      legend=dict(orientation='h'),
      hovermode='x',
    ))

    fig.update_xaxes(dict(
      zeroline=False,
      showgrid=False,
      showticklabels=False,
      range=[
        self.df[self.x_series_name].min(),
        self.df[self.x_series_name].max(),
      ]
    ))
    fig.update_yaxes(dict(
      zeroline=False,  # unless I need it somewhere
      showgrid=False,
      showticklabels=False,
    ))

    self.figs[fig_name] = fig

  def set_x_series_name(self, series_name):
    if series_name not in self.df.columns:
      raise KeyError

    self.x_series_name = series_name

  def add_trace(self, fig_name, series_name, **kwargs):
    trace = dict(
      x=self.df[self.x_series_name],
      y=self.df[series_name],
      name=series_name,
      visible='legendonly',
    )
    
    # Add the custom trace schtuff, if any.
    trace.update(kwargs)
    
    self.figs[fig_name].add_trace(trace)