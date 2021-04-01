import math
import json
import datetime

import pandas as pd

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go


class Plotter(object):
  def __init__(self, df):

    # Even if I don't clean the df here, I should maybe validate it.
    self.df = df
    # self.df = self._validate(df)

    # This list can be used as the children of a html.Div element.
    self.rows = []   

    self._fig_yaxes = {}

    # Memoize for use with @property.
    self._x_stream_label = None

  @property
  def x_stream(self):
    if self._x_stream_label is None:
      return pd.Series(range(len(self.df)), index=self.df.index)
    
    return self.df[self._x_stream_label]

  @property
  def x_stream_text(self):
    if self._x_stream_label == 'time' or self._x_stream_label == 'distance':
      return self.x_stream.apply(lambda x: f'{x} {self.unit_suffix}')

    return self.x_stream

  @property
  def unit_suffix(self):
    if self._x_stream_label == 'time':
      return ' s'
    elif self._x_stream_label == 'distance':
      return ' m'
    else:
      return ''

  def set_x_stream_label(self, stream_label):
    """Set the x data for all xy plots.

    Args:
      stream_label: column label in the DataFrame for the desired stream
        to use as the x data in all plots.
    """
    if stream_label not in self.df.columns:
      raise KeyError(f'There is no stream `{stream_label}` in the DF.')

    self._x_stream_label = stream_label

  def get_fig_by_id(self, id_search):
    # Traverse the layout, which is made up of html.Div rows.
    for row in self.rows:
      # Each row contains 0 or more children:
      # (either dcc.Graph cols or html.Div dummies).
      for child in row.children:
        if isinstance(child, dbc.Col):
          assert len(child.children) == 1
          graph = child.children[0]
          if graph.id == id_search:
            return graph.figure


    # Throw an exception here? Right now it returns 'None'.

  def get_yaxis(self, fig_id, field_name):
    # Find the requested field name's position in the list of fields in
    # the requested fig_id's list, where the position corresponds to the
    # order of the axes.
    axis_index = self._fig_yaxes[fig_id].index(field_name)

    # Convert the axis index to plotly's 1-based axis format.
    return 'y{}'.format(axis_index + 1)

  def add_graph_to_layout(self, new_graph, new_row=False):
    new_graph_col = dbc.Col([new_graph], className='mb-4')
    new_dummy_div = html.Div(id=f'{new_graph.id}_dummy')

    if new_row or len(self.rows) == 0:
      # Create a new row, and place the new graph/fig in it.
      self.rows.append(dbc.Row(
        children=[new_graph_col, new_dummy_div],
      ))
    else:
      # Append the new graph/fig to the end of the last row.
      self.rows[-1].children.extend([new_graph_col, new_dummy_div])

  def init_map_fig(self, fig_id, new_row=False, **kwargs_layout):
    """Initialize a figure that can accept plotly Scattermapbox traces.
    
    TODO:
      * Allow map customization. Both size and content. Maybe outsource
        to other functions, maybe another module in the application.
        Depends how many functions there are.
    """
    layout_dict = dict(
      height=350,
      margin=dict(b=0,t=0,r=0,l=0),
      # margin=dict(b=10,t=0,r=0,l=0),
    )
    layout_dict.update(kwargs_layout)

    map_fig = go.Figure(layout=layout_dict)
    
    map_fig.update_mapboxes(
      style='open-street-map',
      # center_lat=calc_center(lat),
      # center_lon=calc_center(lon),
      zoom=13,
    )

    new_map_graph = dcc.Graph(
      id=fig_id,
      figure=map_fig,  
      config={'doubleClick': False},  # for map_fig only (right?)
    )

    self.add_graph_to_layout(new_map_graph, new_row=new_row)

  def init_xy_fig(self, fig_id, new_row=False, **kwargs_layout):
    # Keep track of this figure's yaxes (none yet).
    self._fig_yaxes[fig_id] = []
    
    layout_dict = dict(
      height=400,
      # margin=dict(b=30,t=0,r=0,l=0),
      margin=dict(b=0,t=0,r=0,l=0),
      #paper_bgcolor='rgba(0,0,0,0)',
      #plot_bgcolor='rgba(0,0,0,0)',
      #legend=dict(yanchor='bottom', y=0.01),
      legend=dict(orientation='h', yanchor='top'),
      showlegend=True,
      hovermode='x',
      #hovermode='x unified',
    )
    layout_dict.update(kwargs_layout)

    fig = go.Figure(layout=layout_dict)

    fig.update_xaxes(dict(
      zeroline=False,
      showgrid=False,
      showticklabels=False,
      range=[
        self.x_stream.min(),
        self.x_stream.max()
      ],
      hoverformat='.0f',
      ticksuffix=self.unit_suffix,
    ))
    fig.update_yaxes(dict(
      zeroline=False,  # unless I need it somewhere
      showgrid=False,
      showticklabels=False,
    ))

    # Create the new graph layout element with accompanying undisplayed
    # div for hover events.
    new_graph = dcc.Graph(
      id=fig_id,
      figure=fig,
      clear_on_unhover=True,
      config=dict(
        clickmode='event+select',
        modebarButtonsToRemove=['hoverClosestCartesian'],
      )
    )

    self.add_graph_to_layout(new_graph, new_row=new_row)

  def add_map_trace(self, map_fig_id, lat_label, lon_label):
    """Create a map trace using plotly's Scattermapbox"""

    # Should I add kwargs? We will see.

    lat = self.df[lat_label]
    lon = self.df[lon_label]

    map_fig = self.get_fig_by_id(map_fig_id)

    map_fig.add_trace(go.Scattermapbox(
      lon=lon,
      lat=lat,
      customdata=self.x_stream,
      # name=source_name,
      hovertemplate=f'%{{customdata:.0f}}{self.unit_suffix}<extra></extra>',
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

  def has_fig(self, fig_id):
    return self.get_fig_by_id(fig_id) is not None

  def add_yaxis(self, fig_id, field_name, **yaxis_kwargs):

    yaxis_kwargs_dft = dict( 
      showticklabels=False,
      showgrid=False,
    )

    yaxis_kwargs_dft.update(yaxis_kwargs)

    # Consult the list of existing yaxes already on this figure, name
    # the new yaxis appropriately, and add kwargs if the new axis will
    # be overlaid (i.e. if it is not a primary yaxis).
    next_yaxis_num = len(self._fig_yaxes[fig_id]) + 1
    next_yaxis_name = 'yaxis{}'.format(next_yaxis_num)

    if next_yaxis_num > 1:
      # Some field is already using the primary yaxis.
      yaxis_kwargs_dft.update(dict(
        # Values that only exist in overlaid axes.
        anchor='x',
        overlaying='y',
        side='right',
      ))

    layout_dict = {next_yaxis_name: yaxis_kwargs_dft}

    self.get_fig_by_id(fig_id).update_layout(layout_dict)

    self._fig_yaxes[fig_id].append(field_name)

  def add_trace(self, fig_id, stream_label, **kwargs):

    trace = dict(
      x=self.x_stream,
      y=self.df[stream_label],
      name=str(stream_label),
      visible='legendonly',
    )
    
    # Add the custom trace schtuff, if any.
    trace.update(kwargs)
    
    # self.figs[fig_name].add_trace(trace)
    self.get_fig_by_id(fig_id).add_trace(trace)
