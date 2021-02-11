import math
import json
import datetime

import plotly.graph_objs as go

import application.labels


def create_map_fig(df, source_name):
  """Create a map figure using mapbox's plotly package.

  Args:
    df (pd.DataFrame): column labels must be StreamLabels.
      This function will look specifically for fields: `lat`, `lon`,
      and (optional) `time`. If `time` is not found, point numbers
      will be used instead.
    source_name (str): The source name to look for the corresponding
      `lat`, `lon`, and `time` streams in the DF.

  Returns:
    map_fig (go.Figure): TODO: Description.
  """
  # Get the columns of the DataFrame from the given source.
  # Then convert the labels to field names.
  df_src = df.act.source(source_name)

  # Should I make this into a DF accessor method? That way,
  # the DF could possibly save its original source name as an attr.
  # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.attrs.html#pandas.DataFrame.attrs
  df_src.columns = df_src.columns.act.field_names

  map_fig = go.Figure(layout=dict(
    height=350,
    margin=dict(b=0,t=0,r=0,l=0),
  ))

  # These will be single-column DFs because they come from a DF
  # broken out by `source_name`.
  lon = df_src['lon']
  lat = df_src['lat']
  customdata = df_src['time'] if 'time' in df_src.columns else range(len(df))

  map_fig.add_trace(go.Scattermapbox(
    lon=lon,
    lat=lat,
    # lon=df.act.loc('lon', source_name),
    # lat=df.act.loc('lat', source_name),
    customdata=customdata,
    name='Full GPS',
    hovertemplate='%{customdata} sec<extra></extra>',
    mode='markers',
  ))

  def calc_center(coord_series):
    return 0.5 * (coord_series.min() + coord_series.max())

  map_fig.update_mapboxes(
    style='open-street-map',
    center_lat=calc_center(lat),
    center_lon=calc_center(lon),
    zoom=13,
  )

  return map_fig


def create_xy_plotter_figs(df):
  """Return multiple plotly figures representing a pd.DataFrame.
  
  Adapted from `create_xy_fig(df)`. This function can provide multiple
  figures, depending on what fields exist in the DataFrame. Developed
  this to keep track of the operations involved with creating multiple
  graph images in my Dash app.

  Args:
    df (pd.DataFrame): column labels must be StreamLabels.
      This function will look specifically for fields: `elevation`,
      `grade`, `speed`, `heartrate`, and `cadence`.

  Returns:
    dict(go.Figure): Maps figure names to plotly Figure instances.

  TODO:
    * Consider that this might go into the dashboard file instead.
      This stuff is Dash-specific. However, I think I like having a
      default series of plots that emerge based on what fields are
      in the DF. I'll figure out how I want to do it.
  """
  plotter = Plotter(df, x_stream_label='time')

  # *** ELEVATION TRACES ***

  plotter.init_fig('elevation')

  # Update the `elevation` figure's default axis.

  # TODO: Make the plot axes more general. For example, if there are no 
  # elevation traces, don't make the elevation axis y1. This affects 
  # hovering from the map onto the xy traces, specifically when I have
  # heart rate without speed.

  # Find the first label with 'elevation' field.
  if df.act.has_field('elevation'):
    elev_labels = df.columns.act.field('elevation')
    elev_lbl = elev_labels[0]

    plotter.figs['elevation'].update_yaxes(
      range=[
        math.floor(df[elev_lbl].min() / 200) * 200,
        math.ceil(df[elev_lbl].max() / 200) * 200
      ],
      ticksuffix=' m',
      hoverformat='.2f',
    )

    # Add matching traces to the `elevation` figure, on the default yaxis.
    for lbl in elev_labels:
      plotter.add_trace('elevation', lbl, visible=True)

  # *** END OF ELEVATION TRACES ***

  # *** GRADE TRACES ***

  if df.act.has_field('grade'):
    grade_labels = df.columns.act.field('grade')

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
    for lbl in grade_labels:
      plotter.add_trace('elevation', lbl, yaxis='y2', visible=True)

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

  speed_labels = df.columns.act.field('speed')
  for lbl in speed_labels:
    speed_text = df[lbl].apply(speed_to_pace)
    plotter.add_trace('speed', lbl, yaxis='y1', text=speed_text, visible=True)

  # *** END OF SPEED / VELOCITY ***

  # *** HEART RATE ***
  
  if df.act.has_field('heartrate'):

    hr_labels = df.columns.act.field('heartrate')

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

    for lbl in hr_labels:
      plotter.add_trace('speed', lbl, yaxis='y2', line=dict(color='#d62728'))

  # *** END OF HEART RATE ***

  # *** CADENCE ***

  if df.act.has_field('cadence'):
    cad_labels = df.columns.act.field('cadence')

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

    for lbl in cad_labels:
      plotter.add_trace('speed', lbl, yaxis='y3', mode='markers', marker=dict(size=2))

  # *** END OF CADENCE ***

  # *** MOVING/STOPPED ***

  # Draw rectangles on the figure corresponding to stopped periods.
  # TODO: Make this into its own function, I think.
  
  if df.act.has_field('moving'):
    # Just pick the first one (hacked together, gross)
    moving_lbl = df.columns.act.field('moving')[0]
    time_lbl = df.columns.act.field('time').act.source(moving_lbl.source_name)[0]

    times_stopped = df[time_lbl].groupby(by=(df[moving_lbl]))

    # Find all the timestamps when strava switches the user from stopped
    # to moving, or from moving to stopped.
    switch_times = df[time_lbl][
      df[moving_lbl].shift(1) != df[moving_lbl]
    ].to_list()

    rect_bounds_all = [
      (
        switch_times[i], 
        switch_times[i+1] - 1
      )
      for i in range(0, len(switch_times) - 1)
    ]

    rect_bounds_all.append((switch_times[-1], df[time_lbl].iloc[-1]))
    
    if df[moving_lbl][0]:
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
  def __init__(self, df, x_stream_label='time'):
    """
    Args:
      x_stream_label (str or labels.StreamLabel): column label for the
        desired x-axis series in the DataFrame. If a string, the first
        column with a StreamLabel bearing the same field_name.
    """
    self.df = df
    #self.fig = self.init_fig()
    self.figs = {}
    self.set_x_stream_label(x_stream_label)

  def init_fig(self, fig_name):
    # Should I add kwargs? We will see.

    fig = go.Figure(layout=dict(height=400))
    
    fig.update_layout(dict(
      margin=dict(b=0,t=0,r=0,l=0),
      #paper_bgcolor='rgba(0,0,0,0)',
      #plot_bgcolor='rgba(0,0,0,0)',
      #legend=dict(yanchor='bottom', y=0.01),
      legend=dict(orientation='h'),
      showlegend=True,
      hovermode='x',
    ))

    fig.update_xaxes(dict(
      zeroline=False,
      showgrid=False,
      showticklabels=False,
      range=[
        self.df[self.x_stream_label].min(),
        self.df[self.x_stream_label].max(),
      ]
    ))
    fig.update_yaxes(dict(
      zeroline=False,  # unless I need it somewhere
      showgrid=False,
      showticklabels=False,
    ))

    self.figs[fig_name] = fig

  def set_x_stream_label(self, stream_label):

    if isinstance(stream_label, str):
      matching_cols = self.df.columns.act.field(stream_label)
      
      # Just pick the first matching stream then.
      stream_label = matching_cols[0]

    elif stream_label not in self.df.columns:
      raise KeyError

    self.x_stream_label = stream_label

  def add_trace(self, fig_name, stream_label, **kwargs):
    if isinstance(stream_label, str):
      matching_cols = self.df.columns.act.field(stream_label)
      
      # Just pick the first matching stream then.
      stream_label = matching_cols[0]

    trace = dict(
      x=self.df[self.x_stream_label],
      y=self.df[stream_label],
      name=str(stream_label),
      visible='legendonly',
    )
    
    # Add the custom trace schtuff, if any.
    trace.update(kwargs)
    
    self.figs[fig_name].add_trace(trace)