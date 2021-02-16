import math
import json
import datetime

import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go

import application.labels


class Plotter(object):
  def __init__(self, df):  # , x_stream_label='time'):
    """
    Args:
      x_stream_label (str or labels.StreamLabel): column label for the
        desired x-axis series in the DataFrame. If a string, the first
        column with a StreamLabel bearing the same field_name.
    """
    # Even if I don't clean the df here, I should validate it.
    self.df = df
    # self.df = self._validate(df)

    # This list can be used as the children of a html.Div element.
    self.rows = []   

    self._fig_yaxes = {}

    # Memoize for use with @property.
    self._x_stream_label = None
    # self.set_x_stream_label(x_stream_label)

  @property
  def x_stream(self):
    if self._x_stream_label is None:
      return pd.Series(range(len(self.df)), index=self.df.index)
    
    return self.df[self._x_stream_label]

  def set_x_stream_label(self, stream_label):

    if isinstance(stream_label, str):
      if not self.df.act.has_field(stream_label):
        raise KeyError(f'There is no field named `{stream_label}` in the DF.')
        
      matching_cols = self.df.columns.act.field(stream_label)
      
      # Just pick the first matching stream then.
      stream_label = matching_cols[0]

    elif stream_label not in self.df.columns:
      raise KeyError(f'There is no stream `{stream_label}` in the DF.')

    self._x_stream_label = stream_label

  def get_fig_by_id(self, id_search):
    # Traverse the layout, which is made up of html.Div rows.
    for row in self.rows:
      # Each row contains 0 or more children:
      # (either dcc.Graph cols or html.Div dummies).
      for child in row.children:
        if isinstance(child, dcc.Graph):
          if child.id == id_search:
            return child.figure

    # Catch an exception here? Right now it returns 'None'.

  def get_yaxis(self, fig_id, field_name):
    # Find the requested field name's position in the list of fields in
    # the requested fig_id's list, where the position corresponds to the
    # order of the axes.
    axis_index = self._fig_yaxes[fig_id].index(field_name)

    # Convert the axis index to plotly's 1-based axis format.
    return 'y{}'.format(axis_index + 1)

  def init_map_fig(self):
    """Initialize a figure that can accept plotly Scattermapbox traces.
    
    TODO:
      * Allow map customization. Both size and content. Maybe outsource
        to other functions, maybe another module in the application.
        Depends how many functions there are.
    """
    map_fig = go.Figure(layout=dict(
      height=350,
      margin=dict(b=0,t=0,r=0,l=0),
    ))
    
    map_fig.update_mapboxes(
      style='open-street-map',
      # center_lat=calc_center(lat),
      # center_lon=calc_center(lon),
      zoom=13,
    )

    # Create a row for the map to have to itself.
    # Add the row at the end of the layout children list/rows.
    self.rows.append(html.Div(
      className='row',  # up for debate
      children=[
        # map
        dcc.Graph(
          id='map',
          className='col',  # up for debate
          figure=map_fig,  
          config={'doubleClick': False},  # for map_fig only (right?)
        ),
        # undisplayed dummy div for hover events
        html.Div(id='map_dummy')
      ],
    ))

  def add_map_trace(self, source_name):
    """Create a map trace using plotly's Scattermapbox"""

    # Should I add kwargs? We will see.

    # Get the columns of the DataFrame from the given source.
    # Then convert the labels to field names.
    df_src = self.df.act.source(source_name)

    # Should I make this into a DF accessor method? That way,
    # the DF could possibly save its original source name as an attr.
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.attrs.html#pandas.DataFrame.attrs
    df_src.columns = df_src.columns.act.field_names

    lon = df_src['lon']
    lat = df_src['lat']

    map_fig = self.get_fig_by_id('map')

    map_fig.add_trace(go.Scattermapbox(
      lon=lon,
      lat=lat,
      customdata=self.x_stream,
      name=source_name,
      hovertemplate='%{customdata} sec<extra></extra>',
      mode='markers',
    ))

    def calc_center(coord_series):
      return 0.5 * (coord_series.min() + coord_series.max())

    # Might need to add a method to center the map on
    # ALL the traces, not just the last one.
    map_fig.update_mapboxes(
      center_lat=calc_center(lat),
      center_lon=calc_center(lon),
    )

  def init_xy_fig(self, fig_name, new_row=False):
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
        self.x_stream.min(),
        self.x_stream.max()
      ]
    ))
    fig.update_yaxes(dict(
      zeroline=False,  # unless I need it somewhere
      showgrid=False,
      showticklabels=False,
    ))

    # Create the new graph layout element with accompanying undisplayed
    # div for hover events.
    new_graph = dcc.Graph(
      id=fig_name,
      className='col',
      figure=fig,
      clear_on_unhover=True,
    )
    new_dummy_div = html.Div(
      id=f'{fig_name}_dummy'
    )

    # row_num starts at 1, not 0.
    if new_row or len(self.rows) == 0:
      # Create a new row, and place the new graph/fig in it.
      self.rows.append(html.Div(
        className='row',
        children=[new_graph, new_dummy_div],
      ))
    else:
      # Append the new graph/fig to the end of the last row.
      self.rows[-1].children.extend([new_graph, new_dummy_div])
  
    # Keep track of this figure's yaxes (none yet).
    self._fig_yaxes[fig_name] = []

  def has_fig(self, fig_id):
    return self.get_fig_by_id(fig_id) is not None

  def add_yaxis(self, fig_id, field_name, **yaxis_kwargs):

    # Consult the list of existing yaxes already on this figure, name
    # the new yaxis appropriately, and add kwargs if the new axis will
    # be overlaid (i.e. if it is not a primary yaxis).
    next_yaxis_num = len(self._fig_yaxes[fig_id]) + 1
    next_yaxis_name = 'yaxis{}'.format(next_yaxis_num)

    if next_yaxis_num > 1:
      # Some field is already using the primary yaxis.
      yaxis_kwargs.update(dict(
        # Values that only exist in overlaid axes.
        anchor='x',
        overlaying='y',
        side='right',
      ))

    layout_dict = {next_yaxis_name: yaxis_kwargs}

    self.get_fig_by_id(fig_id).update_layout(layout_dict)

    self._fig_yaxes[fig_id].append(field_name)

  def add_trace(self, fig_name, stream_label, **kwargs):
    if isinstance(stream_label, str):
      matching_cols = self.df.columns.act.field(stream_label)
      
      # Just pick the first matching stream then.
      stream_label = matching_cols[0]

    trace = dict(
      x=self.x_stream,
      y=self.df[stream_label],
      name=str(stream_label),
      visible='legendonly',
    )
    
    # Add the custom trace schtuff, if any.
    trace.update(kwargs)
    
    # self.figs[fig_name].add_trace(trace)
    self.get_fig_by_id(fig_name).add_trace(trace)


def create_plotter_rows(df, x_stream_label=None):
  """Catch-all controller function for dashboard layout logic.

  Creates a `html.Div.children` list based on streams available
  in the DataFrame:
    - map graph with go.Scattermapbox ('lat' + 'lon')
    - elevation graph with go.Scatter ('elevation' / 'grade'),
    - speed graph with go.Scatter ('speed' / 'cadence' / 'heartrate')

  Args:
    df (pd.DataFrame): A DataFrame with StreamLabels for column labels
    x_stream_label (str or labels.StreamLabel): The desired stream to
      use for the x-axis of the plots. If None, the x-axis will simply
      be point numbers (record numbers). Default None.

  Returns:
    list(html.Div): rows to be used as children of a html.Div element.

  TODO:
    * Find a way to bring the callback creation into this function,
    * or bring this function over to dashboard_activity.
  """  
  plotter = Plotter(df)

  if x_stream_label is not None:
    plotter.set_x_stream_label(x_stream_label)

  # *** Row 1: Map ***

  # Check if there are any sources that have both `lat` and `lon`
  # streams, and add all of them to the map.
  lat_srcs = df.columns.act.field('lat').act.source_names
  lon_srcs = df.columns.act.field('lon').act.source_names
  latlon_srcs = list(set(lat_srcs) & set(lon_srcs))
  
  if len(latlon_srcs) > 0:
    plotter.init_map_fig()
  
  for latlon_src in latlon_srcs:
    # Start up a map fig, row 1, and don't worry about hovering for now.
    plotter.add_map_trace(latlon_src)

  # *** End of Row 1 (map) ***

  # *** Row 2, column 1: ELEVATION TRACES ***

  if df.act.has_field('elevation'):

    # if df.act.has_field('time'):
    #   plotter.set_x_stream_label('time')
    # else:
    #   plotter.set_x_stream_label('distance')
    #   # TODO: if neither of these x-axes exist, just go by record num.
    #   # I think this means re-writing the x-stream logic...

    plotter.init_xy_fig('elevation', new_row=True)

    # Find the first label with this field.
    elev_labels = df.columns.act.field('elevation')
    elev_lbl = elev_labels[0]

    plotter.add_yaxis('elevation', 'elevation',
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

  # *** End of r2c1 (elevation) ***

  # *** Row2, figure 1 alternate field: grade ***
  
  if df.act.has_field('grade'):

    # Initialize the fig if it hasn't happened already.
    if not plotter.has_fig('elevation'):
      plotter.init_xy_fig('elevation', new_row=True)

    plotter.add_yaxis('elevation', 'grade',
      # Same values no matter if axis is primary or not.
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

    # TODO: Consider kwargs to make this call less ambiguous.
    grade_axis = plotter.get_yaxis('elevation', 'grade')
    grade_labels = df.columns.act.field('grade')
    for lbl in grade_labels:
      plotter.add_trace('elevation', lbl, yaxis=grade_axis, visible=True)
 
  # *** r2f1alt (grade) ***

  # *** Row 2, figure 2: Speed ***

  if df.act.has_field('speed'):
    # TODO: How to handle if there is no elevation plot? We wouldn't 
    # want to be in the same row as the map...I smell a revamp...
    # specify the row we want to live on? For now we can just hack it
    # together.
    new_row = not plotter.has_fig('elevation')
    plotter.init_xy_fig('speed', new_row=new_row)

    plotter.add_yaxis('speed', 'speed',
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

  # *** end of r2f2 (speed) ***

  # *** Row2, figure 2 alternate field: heartrate ***
  
  if df.act.has_field('heartrate'):

    # Initialize the fig if it hasn't happened already.
    if not plotter.has_fig('speed'):
      # If we have an elevation plot, we stay in the same row.
      # If we don't have an elevation plot, that either means:
      #   - the current row is the map row, and it gets its own row.
      #   - There are no rows yet.
      # In either case, need to start a new row.
      new_row = not plotter.has_fig('elevation')
      plotter.init_xy_fig('speed', new_row=new_row)
      # TODO: If we are here, heartrate should prob be visible.
      # That goes for several other plot types - let's be systematic.

    plotter.add_yaxis('speed', 'heartrate',
      # Same values no matter if axis is primary or not.
      ticksuffix=' bpm',
      range=[60, 220],
      hoverformat='.0f',
      showticklabels=False,
      showgrid=False,
    )

    # TODO: Consider kwargs to make this call less ambiguous.
    hr_axis = plotter.get_yaxis('speed', 'heartrate')
    hr_labels = df.columns.act.field('heartrate')
    for lbl in hr_labels:
      plotter.add_trace('speed', lbl, yaxis=hr_axis, line=dict(color='#d62728'))

  # *** r2f2alt (heartrate) ***

  # *** row 2, figure 2, alternate field 2: CADENCE ***

  if df.act.has_field('cadence'):

    # Initialize the fig if it hasn't happened already.
    if not plotter.has_fig('speed'):
      # If we have an elevation plot, we stay in the same row.
      # If we don't have an elevation plot, that either means:
      #   - the current row is the map row, and it gets its own row.
      #   - There are no rows yet.
      # In either case, need to start a new row.
      new_row = not plotter.has_fig('elevation')
      plotter.init_xy_fig('speed', new_row=new_row)

    plotter.add_yaxis('speed', 'cadence',
      # Same values no matter if axis is primary or not.
      ticksuffix=' spm',
      range=[60, 220],
      hoverformat='.0f',
      showticklabels=False,
      showgrid=False,
    )

    # TODO: Consider kwargs to make this call less ambiguous.
    cad_axis = plotter.get_yaxis('speed', 'cadence')
    cad_labels = df.columns.act.field('cadence')
    for lbl in cad_labels:
      # TODO: Specify trace colors, typ, or it'll be up to order of plotting.
      plotter.add_trace('speed', lbl, yaxis=cad_axis, mode='markers', marker=dict(size=2))

  # *** END OF CADENCE ***

  # *** MOVING/STOPPED ***

  # Draw rectangles on the figure corresponding to stopped periods.
  # TODO: Make this into its own function, I think.
  
  if df.act.has_field('moving') and plotter.has_fig('speed'):
    # Highlight stopped periods on the speed plot with rectangles.

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

    plotter.get_fig_by_id('speed').update_layout(dict(shapes=shapes,))

  # *** END OF MOVING/STOPPED ***

  return plotter.rows