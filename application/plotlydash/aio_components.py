import math
import re
import uuid

from dash import (dcc, html, dash_table, callback, clientside_callback,
  Input, Output, State, MATCH)
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask import url_for
import pandas as pd
from scipy.interpolate import interp1d
from stravalib.exc import RateLimitExceeded

from application.models import AdminUser
from application.plotlydash.figure_layout import (
  LAT, LON, ELEVATION, GRADE, SPEED, CADENCE, HEARTRATE, POWER,
  AXIS_LAYOUT, TRACE_LAYOUT
)
from application.plotlydash.plots import Plotter
from application.util import labels, units
import power.util as putil


MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'
POWER_ID = 'power'


def id_factory(component, subcomponent):
  def id_func(aio_id):
    return {
      'component': component,
      'subcomponent': subcomponent,
      'aio_id': aio_id,
    }
  return id_func


def init_hover_callbacks_smart(figs=[MAP_ID, ELEVATION_ID, SPEED_ID]):
  for fig_id_from in figs:
    for fig_id_to in figs:
      if fig_id_to == MAP_ID:
        # Mapbox traces appear on a non-default subplot.
        # There should be only one valid curve on the map for now.
        init_callback_force_hover(fig_id_from, fig_id_to, subplot_name='mapbox')
      else:
        # We don't know how many curves will need to be hovered, but since
        # it is just the xy plot, we can hover as many curves as we want.
        # (The map, on the other hand, might have some funky traces with
        # a different number of points.)
        init_callback_force_hover(fig_id_from, fig_id_to, num_curves=10)


def init_callback_force_hover(
  from_id, 
  to_id, 
  num_curves=1,
  subplot_name='xy'
):
  """Synchronizes hover events across separate elements in Dash layout.

  This is done based on pointNumber, which should be reliable as long
  as all the traces being forced to hover come from the same 
  DataFrame. The number of points in each trace will be the same in
  that case, equal to the number of source DataFrame rows.
  
  Additional, unrelated traces on the same figures should not be
  forced to hover. For example, if additional `Scattermapbox` traces
  are on the map figure (representing nearby trails or downsampled
  GPS data). As long as unrelated traces are found in `figure.data`
  AFTER the related traces, they can be excluded from hovering by
  specifying an appropriate `num_curves` value.

  TODO:
    * Relate this more clearly to the the figure-creating function(s).
      These two functions assume a certain figure/dummy naming system,
      so let's have everything live together.

  Args:
    app (dash.Dash): The app whose layout elements will receive
     synchronized hovering.
    from_id (str): The id of the element in the layout that is
      triggering a hover event in another element.
    to_id (str): The id of the element in the layout that is being
      forced to hover by this callback.
    num_curves (int): The number of curves/traces in the target
      element that should be forced to hover. Default 1.
    subplot_name: The name of the subplot that is receiving the forced
      hover event. 'xy' for Scatter, 'mapbox' for Scattermapbox.
      Default 'xy'.
  """
  force_hover_script_template = """
    function(hoverData) {{
      var myPlot = document.getElementById('{0}')
      if (!myPlot.children[1]) {{
        return window.dash_clientside.no_update
      }}
      myPlot.children[1].id = '{0}_js'

      if (hoverData) {{
        // Catch hover events where we have map data that doesn't share
        // the same number of records as our DataFrame. (Relic)
        // if (hoverData.points[0].curveNumber > 1) {{
        //   console.log('No hover');
        //   return window.dash_clientside.no_update
        // }}
        
        var ix = hoverData.points[0].pointIndex

        // Programmatically force hover event. Since we are doing it
        // by pointNumber, we have to specify each curveNumber separately.
        var evt = [];
        for (var i = 0; i < {1}; i++) {{
          evt.push({{curveNumber: i, pointNumber: ix}});
        }}
        
        Plotly.Fx.hover(
          '{0}_js',
          evt,
          '{2}'  // 'mapbox' makes Scattermapbox hovering work
        )

        // Note: Could this script become general by receiving 
        // two inputs? 
        // 1) id of the dcc.Graph (map, elevation, speed)
        // 2) name of the subplot that needs to be hovered
        //    (mapbox, xy, xy2, xy3, etc)
        // Not sure, as the xy hovering works because of the
        // shared hovering. To do curvenumber, I'd need to select
        // each trace's point individually.
        // Hm. I think I will try this out AFTER this commit, when I
        // Play around with multiple traces on the map.
        // Could change the map's hovering to select
        // all nearby points when one pointNumber is selected.
        // Possible?
        //
        // Thought some more, and realized I will want special hovering
        // from one map trace to another - if I map-match, I'll want to
        // show the matched point that corresponds to the hovered point.
        // And that might not be close. So I think hovering a point on
        // the map might need to be its own script (not combined with
        // this script.)

      }}
      return window.dash_clientside.no_update
    }}
  """

  clientside_callback(
    force_hover_script_template.format(to_id, num_curves, subplot_name),
    # Can use any 'data-*' wildcard property, and they
    # must be unique for each graph to hover.
    Output('{}_dummy'.format(from_id), 'data-{}'.format(to_id)),
    [Input(from_id, 'hoverData')],
  )


class FigureDivAIO(html.Div):
  """
    Refs:
    https://dash.plotly.com/all-in-one-components#example-2:-datatableaio---sharing-data-between-__init__-and-callback
  """
  class ids:
    store = id_factory('FigureDivAIO', 'store')
    options = id_factory('FigureDivAIO', 'row')
    xselector = id_factory('FigureDivAIO', 'xselector')
    figures = id_factory('FigureDivAIO', 'div')
  ids = ids

  def __init__(self, df=None, aio_id=None):
    """All-in-One component that is composed of a parent `html.Div`
    with a `dcc.Store` and a `dash_table.DataTable` as children.

    Args:
      df (pandas.DataFrame): the activity data. 
      aio_id: the All-in-One component ID used to generate the `dcc.Store`
        component's dictionary ID.
    """
    if aio_id is None:
      aio_id = str(uuid.uuid4())
    self.aio_id = aio_id

    # Store the DataFrame in `dcc.Store`
    # store_data = df.to_dict('records') if isinstance(df, pd.DataFrame) else None
    # if df is not None and isinstance(df, pd.DataFrame):
    #   store_data = self.data_from_df(df)
    # else:
    if df is None:
      raise Exception('No data supplied. Pass in a dataframe as `df=`')
    elif not isinstance(df, pd.DataFrame):
      raise TypeError('`df` must be a pandas.DataFrame')

    # Initialize the html.Div with a list of its children components. 
    super().__init__([
      dcc.Store(data=self.data_from_df(df), id=self.ids.store(aio_id)),
      dbc.Row(self._create_plot_opts(df)),
      dbc.Spinner(
        html.Div(
          children=[html.Div(style={'height': '400px'})],
          id=self.ids.figures(aio_id)
        ),
      )
    ])

  @classmethod
  def data_from_df(cls, df):
    return df.to_dict('records')

  @classmethod
  def df_from_data(cls, data):
    return pd.DataFrame.from_records(data)

  def _create_plot_opts(self, df):
    # Provide a list of x-axis options, with records included by default.
    x_stream_opts = ['record']
    for x in ['time', 'distance']:
      if x in df.columns:
        x_stream_opts.append(x)

    x_stream_radiogroup = dbc.Row([
      dbc.Label('Select x-axis stream:'),
      dbc.RadioItems(
        options=[{'label': x, 'value': x} for x in x_stream_opts],
        value=x_stream_opts[0],
        # id='x-selector',
        id=self.ids.xselector(self.aio_id),
        inline=True
      ),
    ])

    available_figs = []
    # Determine which figures are available based on DataFrame columns. 
    # 'map', 'elevation', 'speed' (, 'power')
    if df.fld.has(LAT, LON):
      available_figs.append(MAP_ID)
    if df.fld.has(ELEVATION) or df.fld.has(GRADE):
      available_figs.append(ELEVATION_ID)
    if df.fld.has(SPEED) or df.fld.has(HEARTRATE) or df.fld.has(POWER):
      available_figs.append(SPEED_ID)
    plot_checkgroup = dbc.Row([
      dbc.Label('Select visible plots:'),
      dbc.Checklist(
        options=[{'label': x, 'value': x} for x in available_figs],
        value=available_figs,
        id='plot-checklist',
        inline=True
      ),
    ])

    # TODO: Now we know which figures are available - feed them into a
    # new function that initializes all the hovers based on available
    # figs. (Not working to define callback-in-a-callback rn)
    # https://community.plotly.com/t/dynamic-controls-and-dynamic-output-components/5519
    # init_hover_callbacks_smart(app, available_figs)

    return [
      dbc.Col(x_stream_radiogroup),
      # dbc.Col(plot_checkgroup),
    ]

  # @callback(
  #   Output(ids.options(MATCH), 'children'),
  #   Input(ids.store(MATCH), 'data'),
  # )
  # def create_plot_opts(record_data):
  #   if record_data is None:
  #     raise PreventUpdate

  #   df = FigureDivAIO.df_from_data(record_data)

  #   return FigureDivAIO._create_plot_opts(df)

  @callback(
    Output(ids.figures(MATCH), 'children'),
    Input(ids.xselector(MATCH), 'value'),
    # Input('plot-checklist', 'values'),
    State(ids.store(MATCH), 'data'),
  )
  def update_figures(x_stream, record_data):
    if record_data is None:
      raise PreventUpdate

    df = FigureDivAIO.df_from_data(record_data)

    if x_stream == 'record':
      x_stream = None

    return FigureRowsAIO(df, x_stream_label=x_stream)

  init_hover_callbacks_smart()


class FigureRowsAIO(html.Div):
  """Catch-all controller for figure layout logic.

  Creates a list of elements for use as `html.Div.children` based on
  streams available in the DataFrame:
    - map graph with go.Scattermapbox ('lat' + 'lon')
    - elevation graph with go.Scatter ('elevation' / 'grade'),
    - speed graph with go.Scatter ('speed' / 'cadence' / 'heartrate')

  Args:
    df (pd.DataFrame): A DataFrame representing a recorded activity.
      Each row represents a record, and each column represents a stream
      of data.
    x_stream_label (str): column label in the DataFrame for the desired stream
      to use as the x-data in all xy plots. If None, x-data will simply
      be point numbers (record numbers). Default None.

  Returns:
    list(html.Div): rows to be used as children of a html.Div element.
  """
  def __init__(self, df=None, x_stream_label=None, aio_id=None):
    if df is None:
      raise Exception('No data supplied. Pass in a dataframe as `df=`')
    
    plotter = Plotter(df)

    if x_stream_label is not None:
      plotter.set_x_stream_label(x_stream_label)

    # *** Row 1: Map ***

    # Check if there are both `lat` and `lon` streams, and create a map
    # if so.
    if df.fld.has(LAT, LON): 
      plotter.init_map_fig(MAP_ID)
    
      # TODO: Make the plotly figure generation part of hns?
      plotter.add_map_trace(MAP_ID, lat_label=LAT, lon_label=LON,
        # map trace kwargs here, if desired.
      )
      # map_graph = figures.Map(MAP_ID)
      # map_graph.add_trace(x_stream=x_stream_label or 'record')

    # *** End of Row 1 (map) ***

    # *** Row 2 (elevation and speed graphs) ***

    if df.fld.has(ELEVATION):

      plotter.init_xy_fig(ELEVATION_ID, new_row=True)

      plotter.add_yaxis(ELEVATION_ID, ELEVATION, **AXIS_LAYOUT[ELEVATION])

      # Add trace to the `elevation` figure, on the default yaxis.
      plotter.add_trace(ELEVATION_ID, ELEVATION,
        formatter=lambda meters: f'{meters*units.FT_PER_M:.0f} ft',
        visible=True,
        **TRACE_LAYOUT[ELEVATION]
      )
    
    if df.fld.has(GRADE):

      # Initialize the fig if it hasn't happened already.
      if not plotter.has_fig(ELEVATION_ID):
        plotter.init_xy_fig(ELEVATION_ID, new_row=True)

      plotter.add_yaxis(ELEVATION_ID, GRADE, **AXIS_LAYOUT[GRADE])

      grade_axis = plotter.get_yaxis(ELEVATION_ID, GRADE)
      plotter.add_trace(ELEVATION_ID, GRADE,
        formatter=lambda g_pct: f'{g_pct:.1f}%',
        yaxis=grade_axis,
        visible=True
      )

    if df.fld.has(SPEED):
      # TODO: How to handle if there is no elevation plot? We wouldn't 
      # want to be in the same row as the map...I smell a revamp...
      # specify the row we want to live on? For now we can just hack it
      # together.
      new_row = not plotter.has_fig(ELEVATION_ID)
      plotter.init_xy_fig(SPEED_ID, new_row=new_row)

      plotter.add_yaxis(SPEED_ID, SPEED, **AXIS_LAYOUT[SPEED])

      if df.fld.has('GAP'):
        plotter.add_trace(SPEED_ID,
          'GAP',
          formatter=units.speed_to_pace,
          visible=True,
          line_color='#FC4C02',
          **TRACE_LAYOUT[SPEED]
        )

      if df.fld.has('NGP'):
        plotter.add_trace(SPEED_ID,
          'NGP',
          formatter=units.speed_to_pace,
          visible=True,
          line_color='#204D74',
          **TRACE_LAYOUT[SPEED]
        )

      plotter.add_trace(SPEED_ID, SPEED,
        formatter=units.speed_to_pace,
        visible=True,
        line_color='black',
        **TRACE_LAYOUT[SPEED]
      )
    
    if df.fld.has(HEARTRATE):

      # Initialize the fig if it hasn't happened already.
      if not plotter.has_fig(SPEED_ID):
        # If we have an elevation plot, we stay in the same row.
        # If we don't have an elevation plot, that either means:
        #   - the current row is the map row, and it gets its own row.
        #   - There are no rows yet.
        # In either case, need to start a new row.
        new_row = not plotter.has_fig(ELEVATION_ID)
        plotter.init_xy_fig(SPEED_ID, new_row=new_row)
        # TODO: If we are here, heartrate should prob be visible.
        # That goes for several other plot types - let's be systematic.

      plotter.add_yaxis(SPEED_ID, HEARTRATE, **AXIS_LAYOUT[HEARTRATE])

      # TODO: Consider kwargs to make this call less ambiguous.
      hr_axis = plotter.get_yaxis(SPEED_ID, HEARTRATE)
      plotter.add_trace(SPEED_ID, HEARTRATE, yaxis=hr_axis,
        formatter=lambda hr: f'{hr:.0f} bpm',
        visible=True,
        **TRACE_LAYOUT[HEARTRATE]
      )

    if df.fld.has(CADENCE):

      # Initialize the fig if it hasn't happened already.
      if not plotter.has_fig(SPEED_ID):
        # If we have an elevation plot, we stay in the same row.
        # If we don't have an elevation plot, that either means:
        #   - the current row is the map row, and it gets its own row.
        #   - There are no rows yet.
        # In either case, need to start a new row.
        new_row = not plotter.has_fig(ELEVATION_ID)
        plotter.init_xy_fig(SPEED_ID, new_row=new_row)

      plotter.add_yaxis(SPEED_ID, CADENCE, **AXIS_LAYOUT[CADENCE])

      # TODO: Consider kwargs to make this call less ambiguous.
      cad_axis = plotter.get_yaxis(SPEED_ID, CADENCE)

      # TODO: Specify trace colors, typ, or it'll be up to order of plotting.
      plotter.add_trace(SPEED_ID, CADENCE,
        yaxis=cad_axis,
        formatter=lambda hr: f'{hr:.0f} spm',
        **TRACE_LAYOUT[CADENCE]
      )

    # NEW power and flat-ground speed traces.
    if df.fld.has(POWER):
      plotter.add_yaxis(SPEED_ID, POWER, **AXIS_LAYOUT[POWER])
      pwr_axis = plotter.get_yaxis(SPEED_ID, POWER)

      plotter.add_trace(SPEED_ID, POWER,
        formatter=lambda pwr: f'{pwr:.2f} W/kg',
        yaxis=pwr_axis,
        **TRACE_LAYOUT[POWER]
      )

    # Draw rectangles on the speed figure for strava stopped periods.
    # TODO: Make this into its own function, I think.
    
    if df.fld.has('moving') and plotter.has_fig(SPEED_ID):
      plotter.get_fig_by_id(SPEED).add_trace(dict(
        x=plotter.x_stream,
        y=[0.0 for _ in range(len(plotter.x_stream))],
        text=['Moving' if moving else 'Stopped' for moving in plotter.df['moving']],
        hovertemplate='%{text}<extra></extra>',
        mode='markers',
        marker_color=['green' if moving else 'red' for moving in plotter.df['moving']],
        marker_size=2,
        # yaxis=pwr_axis,
      ))

      # # Highlight stopped periods on the speed plot with rectangles.

      # # Find all the timestamps when strava switches the user from stopped
      # # to moving, or from moving to stopped.
      # stopped_ixs = df.index[~df['moving']]
      # stopped_periods_start_ixs = stopped_ixs[
      #   stopped_ixs.to_series().diff() != 1]
      # stopped_periods_end_ixs = stopped_ixs[
      #   stopped_ixs.to_series().diff(-1) != -1]

      # fig_with_stops = plotter.get_fig_by_id(SPEED_ID)

      # for i in range(len(stopped_periods_start_ixs)):
      #   start_ix = stopped_periods_start_ixs[i]
      #   end_ix = stopped_periods_end_ixs[i]

      #   if start_ix == end_ix:
      #     # A single point - use a line, not a rectangle.
      #     fig_with_stops.add_vline(
      #       # x=df['time'][start_ix],
      #       x=plotter.x_stream[start_ix],
      #       line_color='red',
      #       opacity=0.5,
      #     )
      #   else:
      #     fig_with_stops.add_vrect(
      #       # x0=df['time'][start_ix],
      #       # x1=df['time'][end_ix],
      #       x0=plotter.x_stream[start_ix],
      #       x1=plotter.x_stream[end_ix],
      #       #layer='below',
      #       #line={'width': 0}, 
      #       line_color='red',
      #       #fillcolor='LightSalmon',
      #       fillcolor='red',
      #       opacity=0.5,
      #     )

    # *** End of row 2 (elevation and speed) ***

    # TODO: Define these callbacks dynamically, eg
    # `init_hover_callbacks_smart(figs=plotter.fig_ids)`
    init_hover_callbacks_smart()
  
    super().__init__(plotter.rows)


class TimeInput(dbc.Input):
  def __init__(self, *args, **kwargs):
    total_secs = kwargs.pop('seconds', 0)

    # TODO: Remove duplicate kwargs if they are passed,
    # and warn the user.
    derived_kwargs = kwargs.copy()

    total_secs_int = round(total_secs)

    hours = math.floor(total_secs_int / 3600.0)
    minutes = math.floor(total_secs_int / 60.0) - hours * 60
    seconds = total_secs_int - minutes * 60 - hours * 3600

    super().__init__(
      *args,
      type='string',
      placeholder='HH:MM:SS',
      pattern='[0-9][0-9]:[0-5][0-9]:[0-5][0-9]',
      value=f'{hours:02d}:{minutes:02d}:{seconds:02d}',
      debounce=True,
      style={
        'max-width': '100px',
        'min-width': '100px'
      },
      **derived_kwargs
    )


def validate_time_str(time_str):
  return time_str is not None and re.match('[0-9][0-9]:[0-5][0-9]:[0-5][0-9]', time_str)


class TssDivAIO(html.Div):
  class ids:
    ngp = id_factory('TssDivAIO', 'ngp')
    ftp = id_factory('TssDivAIO', 'ftp')
    total_time = id_factory('TssDivAIO', 'total')
    tss_per_ftp_hr = id_factory('TssDivAIO', 'tss_per_ftp_hr')
    intensity = id_factory('TssDivAIO', 'intensity')
    tss = id_factory('TssDivAIO', 'tss')

  def __init__(self, ngp=None, ftp=None, total_time=None, aio_id=None):
    """
    ngp: Normalized Graded Pace for this activity, in meters per second.
    ftp: Functional Threshold Pace for this athlete, in meters per second.
    """
    if ngp is None:
      raise Exception(
        'Insufficient data supplied. Pass in Normalized Graded Pace as `ngp=`'
      )
    if ftp is None:
      raise Exception(
        'Insufficient data supplied. Pass in Functional Threshold Pace '
        ' as `ftp=`'
      )
    if total_time is None:
      raise Exception(
        'Insufficient data supplied. Pass in integer seconds as `total_time=`'
      )
    if aio_id is None:
      aio_id = str(uuid.uuid4())

    super().__init__([
      html.Div(
        [
          html.Div(
            [
              dbc.FormText('Functional Threshold Pace'),
              TimeInput(
                id=self.ids.ftp(aio_id),
                # seconds=units.speed_to_timedelta(ftp).total_seconds()
                seconds=units.M_PER_MI / ftp
              ),
            ],
            className='block'
          ),
          html.Div(
            html.I(className='fa-solid fa-divide'),
            # className='d-flex align-items-center justify-content-center',
          ),
          html.Div(
            [
              dbc.FormText('Normalized Graded Pace'),
              TimeInput(
                id=self.ids.ngp(aio_id),
                seconds=units.M_PER_MI / ngp
              ),
            ],
            className='block'
          )
        ],
        # className='d-flex flex-column flex-lg-row justify-content-center',
        id='equation-1'
      ),
      dbc.Row(
        html.I(className='fa-solid fa-down-long fa-2xl my-4'),
        justify='center',
      ),
      html.Div(
        [
          html.Div(
            [
              dbc.FormText('Total Time'),
              TimeInput(id=self.ids.total_time(aio_id), seconds=total_time),
            ],
            id='total-time-block',
            className='block'
          ),
          html.Div(html.I(className='fa-solid fa-multiply')),
          html.Div(
            [
              html.Div(
                [
                  dbc.FormText('Intensity Factor'),
                  dbc.Input(
                    type='number', 
                    id=self.ids.intensity(aio_id),
                    min=0, max=2, step=0.001,
                    placeholder='IF',
                    style={'width': '100px'}
                  ),
                ],
              ),
              html.I(className='fa-solid fa-2'),
            ],
            id='if-block',
            className='block'
          ),
          html.Div(html.I(className='fa-solid fa-multiply')),
          html.Div(
            [
              dbc.FormText('TSS per hour'),
              dbc.Input(
                id=self.ids.tss_per_ftp_hr(aio_id),
                type='number',
                value=100,
                style={'width': '100px'}
              ),
            ],
            id='points-block',
            className='block'
          ),
        ],
        id='equation-2'
      ),
      dbc.Row(
        html.I(className='fa-solid fa-down-long fa-2xl my-4'),
        justify='center',
      ),
      dbc.Row(
        html.Div(
          [
            dbc.FormText('TSS'),
            dbc.Input(
              type='number', 
              id=self.ids.tss(aio_id),
              min=0, max=1000, step=0.1,
              placeholder='TSS',
              style={'width': '100px'}
            ),
          ],
          className='block'
        ),
        justify='center',
      )
    ])

  @callback(
    Output(ids.intensity(MATCH), 'value'),
    Input(ids.ngp(MATCH), 'value'),
    Input(ids.ftp(MATCH), 'value'),
  )
  def update_intensity_factor(ngp_str, ftp_str):

    if not validate_time_str(ngp_str) or not validate_time_str(ftp_str):
      raise PreventUpdate

    ngp_secs_per_mile = units.string_to_seconds(ngp_str)
    ftp_secs_per_mile = units.string_to_seconds(ftp_str)

    intensity_factor = ftp_secs_per_mile / ngp_secs_per_mile
    
    return round(intensity_factor, 3)

  @callback(
    Output(ids.tss(MATCH), 'value'),
    Input(ids.intensity(MATCH), 'value'),
    Input(ids.total_time(MATCH), 'value'),
    Input(ids.tss_per_ftp_hr(MATCH), 'value')
  )
  def update_tss(intensity_factor, total_time_str, tss_per_ftp_hr):

    if (
      intensity_factor is None 
      or not validate_time_str(total_time_str)
      or tss_per_ftp_hr is None
    ):
      raise PreventUpdate

    total_hours = units.string_to_seconds(total_time_str) / 3600

    tss = tss_per_ftp_hr * total_hours * intensity_factor ** 2

    return round(tss, 1)


class StatsDivAIO(dbc.Accordion):
  class ids:
    table = id_factory('StatsDivAIO', 'table')
    intensity = lambda aio_id: TssDivAIO.ids.intensity(aio_id)
    tss = lambda aio_id: TssDivAIO.ids.tss(aio_id)
    ngp = lambda aio_id: TssDivAIO.ids.ngp(aio_id)

  def __init__(self, *args, df=None, aio_id=None, **kwargs):
    if df is None:
      raise Exception('No data supplied. Pass in a dataframe as `df=`')
    
    if aio_id is None:
      aio_id = str(uuid.uuid4())
    self.aio_id = aio_id
    
    # WIP
    # from power.algorithms import trainingpeaks
    # ngp_rolling = power.util.sma(ngp_array, 30)
    # ngp_val = power.util.lactate_norm(ngp_rolling[29:])
    # ngp_val = trainingpeaks.ngp_val(ngp_array)  # best option; assumes 1 sec samples
    # tss = trainingpeaks.training_stress_score(ngp_val, ftp, duration_secs)
    # tss = trainingpeaks.training_stress_score(v_array, g_array)  # assumes 1-second samples
    # tss = trainingpeaks.training_stress_score(ngp_array)  # assumes 1-second samples
    if 'NGP' in df.columns:
      # Resample the NGP stream at 1 sec intervals
      # TODO: Figure out how/where to make this repeatable.
      # 1sec even samples make the math so much easier.
      interp_fn = interp1d(df['time'], df['NGP'], kind='linear')
    elif SPEED in df.columns:
      interp_fn = interp1d(df['time'], df[SPEED], kind='linear')
    else:
      # There just isn't enough data in the DF to make this div interesting.
      super().__init__(
        [],
        *args,
        start_collapsed=True,
        **kwargs
      )
      return

    ngp_1sec = interp_fn([i for i in range(df['time'].max())])

    # Apply a 30-sec rolling average.
    window = 30
    ngp_rolling = pd.Series(ngp_1sec).rolling(window).mean()
    # ngp_sma = putil.sma(
    #   df['NGP'], 
    #   window,
    #   time_series=df['time']
    # )

    ngp_ms = putil.lactate_norm(ngp_rolling[29:])

    df_stats = self._calc_stats_df(df)

    super().__init__(
      [
        dbc.AccordionItem(
          html.Div(self.create_moving_table(df_stats)),
          title='Pace Comparison',
        ),
        dbc.AccordionItem(
          TssDivAIO(
            aio_id=aio_id,
            ftp=AdminUser().ftp_ms,
            ngp=ngp_ms,
            total_time=df['time'].iloc[-1]-df['time'].iloc[0]
          ),
          title='Training Stress Score details'
        ),
      ],
      *args,
      start_collapsed=True,
      **kwargs,
    )

  def _calc_stats_df(self, df):
    """Calculate summary stats."""

    if df.fld.has('distance'):
      df_stats = pd.DataFrame([])

      df_stats.loc['Total', 'Time (s)'] = df['time'].diff(1).sum()
      df_stats.loc['Total', 'Distance (m)'] = df['distance'].diff(1).sum()

      if df.fld.has('moving'):
        # Count time and distance if the user was moving at the START
        # of the interval.
        df_stats.loc['Moving', 'Time (s)'] = df['time'].diff(1)[df['moving'].shift(1, fill_value=False)].sum()
        
        # Not quite right - strava is doing something sophisticated...
        # working on it.
        df_stats.loc['Moving (Strava)', 'Time (s)'] = df['time'].diff(1)[df['moving'].shift(1, fill_value=False)].sum()
        
        df_stats.loc['Moving', 'Distance (m)'] = df['distance'].diff(1)[df['moving'].shift(1, fill_value=False)].sum()
        df_stats.loc['Moving (Strava)', 'Distance (m)'] = df_stats.loc['Total', 'Distance (m)']

      df_stats['Speed (m/s)'] = df_stats['Distance (m)'] / df_stats['Time (s)']
      df_stats['Distance (mi)'] = df_stats['Distance (m)'].astype('float') / units.M_PER_MI
      df_stats['Time'] = df_stats['Time (s)'].apply(units.seconds_to_string)
      df_stats['Pace'] = df_stats['Speed (m/s)'].apply(units.speed_to_pace)

      return df_stats

  def create_moving_table(self, df_stats):
    df_stats.insert(0, '', df_stats.index)
    
    return dash_table.DataTable(
      data=df_stats.to_dict('records'),
      columns=self._create_moving_table_cols(df_stats.columns),
      id=self.ids.table(self.aio_id),
      style_cell={
        'whiteSpace': 'normal',
        'height': 'auto',
      },
    )

  @staticmethod
  def _create_moving_table_cols(cols):
    return [
      {'name': i, 'id': i, 'type': 'numeric', 'format': {'specifier': '.2f'}}
      if (i.startswith('Distance') or i.startswith('Speed')) else
      {'name': i, 'id': i}
      for i in cols
      if i not in ['Time (s)', 'Distance (m)', 'Speed (m/s)']
    ]


class SettingsLabel(dbc.Label):
  def __init__(self, *args, 
    width=5,
    sm=5,
    md=4,
    lg=3,
    xl=2,
    **kwargs
  ):
    super().__init__(*args, 
      width=width,
      sm=sm,
      md=md,
      lg=lg,
      xl=xl,
      **kwargs
    )


class StravaAccountRow(dbc.Row):

  def __init__(self, strava_account, *args, **kwargs):
    try:
      super().__init__(
        class_name='py-3',
        justify='center',
        children=dbc.Col(
          xl=9,
          children=dbc.Card(
            style={'border-radius': '15px'},
            children=dbc.CardBody(
              class_name='p-4',
              children=html.Div(
                className='d-flex text-black',
                children=[
                  html.Div(
                    className='flex-shrink-0',
                    children=html.A(
                      href=strava_account.url,
                      children=html.Img(
                        src=strava_account.profile_picture_url,
                        alt='Athlete Profile Picture',
                        className='img-fluid',
                        style={'width': '180px', 'border_radius': '10px'}
                      )
                    )                    
                  ),
                  html.Div(
                    className='flex-grow-1 ms-3',
                    children=[
                      html.A(
                        href=strava_account.url,
                        children=html.H5(
                          className='mb-1',
                          children=f'{strava_account.firstname} {strava_account.lastname}'
                        )
                      ),
                      html.P(
                        className='mb-2 pb-1',
                        style={'color': '#2b2a2'},
                        children=f'Strava Account #{strava_account.strava_id}'
                      ),
                      html.P(
                        className='mb-2 pb-1',
                        style={'color': '#2b2a2'},
                        children=f'{strava_account.athlete.city}, {strava_account.athlete.state}, {strava_account.athlete.country}'
                      ),
                      html.Div(
                        className='d-flex justify-content-start '
                                  'rounded-3 p-2 mb-2',
                        style={'background-color': '#efefef'},
                        children=[
                          html.Div([
                            html.P(
                              className='small text-muted mb-1',
                              children='Runs'
                            ),
                            html.P(
                              className='mb-0',
                              children=strava_account.run_count
                            ),
                          ]),
                          html.Div(
                            className='px-3',
                            children=[
                              html.P(
                                className='small text-muted mb-1',
                                children='Followers'
                              ),
                              html.P(
                                className='mb-0',
                                children=strava_account.follower_count
                              ),                              
                            ]
                          )
                        ]
                      ),
                      html.Div(
                        className='d-flex pt-1',
                        children=[
                          dbc.Button(
                            href=f'/strava/activities?id={strava_account.strava_id}',
                            color='primary',
                            class_name='me-1 flex-grow-1',
                            external_link=True,
                            children='View Strava Activities'
                          ),
                          dbc.Button(
                            href=url_for(
                              'strava_api.revoke',
                              id=strava_account.strava_id
                            ),
                            color='danger',
                            class_name='flex-grow-1',
                            external_link=True,
                            children='Revoke Access'
                          )
                        ]
                      )
                    ]
                  )
                ]
              )
            )
          )
        )
      )
    except RateLimitExceeded:
      super().__init__('Rate limit exceeded')
