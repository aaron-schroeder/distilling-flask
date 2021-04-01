import datetime
import json
import math
import os

from dash import Dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_table
import dateutil
import numpy as np
import pandas as pd
import plotly.graph_objs as go

from application import converters, stravatalk, labels, util
from application.plotlydash.plots import Plotter
# TODO: Consider bringing remaining items in `layout` into this module.
from application.plotlydash import layout
from application.plotlydash.layout import (
  MAP_ID, ELEVATION_ID, SPEED_ID
)
from application.plotlydash.figure_layout import (
  LAT, LON, ELEVATION, GRADE, SPEED, CADENCE, HEARTRATE, POWER,
  AXIS_LAYOUT, TRACE_LAYOUT
)


def create_dash_app(df):
  """Construct single-page Dash app for activity data display from DF.
  
  Mostly for debugging purposes.

  Args:
    df (pandas.DataFrame): Activity data, with each row a record, and
      each column a data stream.
  """
  app = Dash(
    __name__,
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
    ],
    
    # Script source: local download of the plotly mapbox distribution.
    # Since the script is in assets/ and supplies the global Plotly var,
    # it is used over the other plotly packages by default.
    # (Modified to make my programmatic hover-on-map stuff work). 
    # It includes everything I need:
    # scatter, scattermapbox, choroplethmapbox and densitymapbox
    # https://github.com/plotly/plotly.js/blob/master/dist/README.md#partial-bundles

    # Turn this on to avoid using local scripts by loading from cdn.
    # Note: Local scripts are by default from `async-plotlyjs.js`, which is
    # minified and incomprehensible when debugging. Using plotly-mapbox,
    # for example, allows me to see what is going on for easier debugging
    # and future edits to the script itself.
    # https://community.plotly.com/t/smaller-version-of-async-plotlyjs-js-its-so-big-and-loads-so-slow/42247/2
    # https://github.com/plotly/dash-docs/issues/723#issuecomment-656393396
    # https://github.com/plotly/plotly.js/blob/master/dist/README.md#partial-bundles
    # external_scripts=[
    #   #'https://cdn.plot.ly/plotly-basic-1.54.3.min.js',
    #   'https://cdn.plot.ly/plotly-mapbox-1.58.4.js'
    # ],
  )

  app.layout = layout.init_layout()

  calc_power(df)

  data_store = app.layout.children[3]
  assert data_store.id == 'activity-data'
  data_store.data = df.to_dict('records')

  init_figure_callbacks(app)
  init_stats_callbacks(app)

  return app


def calc_power(df):
  """Add power-related columns to the DataFrame.
  
  Note: Honestly need to figure out how I handle calcs in general.

  """
  if df.fld.has('speed'):
    from power import adjusted_pace

    if df.fld.has(GRADE):
      # df['power_inst'] = power.o2_power_ss(df['speed'], df['grade'] / 100.0)
      # # My power series is intended to mimic O2 consumption - assuming
      # # the athlete stays in the moderate domain.
      # df['power'] = power.o2_power(
      #   df['speed'],
      #   grade_series=df['grade'] / 100.0,
      #   time_series=df['time'],
      #   #tau=10,
      # )

      # df['equiv_speed'] = df['power_inst'].apply(adjusted_pace.power_to_flat_speed)
      
      df['equiv_speed'] = [adjusted_pace.equiv_flat_speed(s, g / 100) for s, g in zip(df['speed'], df['grade'])]
      df['NGP'] = [adjusted_pace.ngp(s, g / 100) for s, g in zip(df['speed'], df['grade'])]
      df['GAP'] = [adjusted_pace.gap(s, g / 100) for s, g in zip(df['speed'], df['grade'])]
      
    # else:
    #   # Flat-ground power.
    #   df['power_inst'] = power.o2_power_ss(df['speed'])
    #   df['power'] = power.o2_power(
    #     df['speed'],
    #     time_series=df['time'],
    #   )


def init_stats_callbacks(app):
  @app.callback(
    Output('stats', 'children'),
    # Output('calc-stats', 'data'),
    Input('activity-data', 'data'),
  )
  def update_stats(record_data):
    if record_data is None:
      raise PreventUpdate

    df = pd.DataFrame.from_records(record_data)

    if 'grade' in df.columns:
      # Resample the NGP stream at 1 sec intervals
      # TODO: Figure out how/where to make this repeatable.
      # 1sec even samples make the math so much easier.
      from scipy.interpolate import interp1d
      interp_fn = interp1d(df['time'], df['NGP'], kind='linear')
      ngp_1sec = interp_fn([i for i in range(df['time'].max())])

      # Apply a 30-sec rolling average.
      from power import util as putil
      
      window = 30
      ngp_rolling = pd.Series(ngp_1sec).rolling(window).mean()
      
      # ngp_sma = putil.sma(
      #   df['NGP'], 
      #   window,
      #   time_series=df['time']
      # )

      ngp_val = putil.lactate_norm(ngp_rolling[29:])
      # ngp_val = putil.lactate_norm(ngp_sma[df['time'] > 29])
      # intensity_factor = ngp_val / util.pace_to_speed('6:30')
      # tss = (110.0 / 3600) * df['time'].iloc[-1] * intensity_factor ** 2

      # ngp_string = util.speed_to_pace(ngp_val)
      # ngp_text = (
      #   f'NGP = {ngp_string}, IF = {intensity_factor:.2f}, '
      #   f'TSS = {tss:.1f}'
      # )
      ngp_td = util.speed_to_timedelta(ngp_val)
      total_secs = ngp_td.total_seconds()
      hours = math.floor(total_secs / 3600.0)
      mins = math.floor(total_secs / 60)
      secs = round(total_secs - mins * 60)
      # secs = math.floor(total_secs * 60.0 % 60))

    else:
      hours, mins, secs = 23, 59, 59

    df_stats = calc_stats_df(df)

    stats_div = html.Div([
      html.Div(create_moving_table(df_stats)),
      dbc.Row([
        dbc.Col(
          [
            dbc.FormGroup([
              dbc.Label('CP:'),
              dbc.InputGroup([
                dbc.Input(
                  type='number', 
                  id='cp-min',
                  min=0, max=59,
                  placeholder='MM',
                  value=6,
                ),
                dbc.InputGroupAddon(':'),
                dbc.Input(
                  type='number', 
                  id='cp-sec',
                  min=0, max=59,
                  placeholder='SS',
                  value=30,
                ),
              ]),
            ]),
          ],
          width=3,
        ),
        dbc.Col(
            [
            dbc.FormGroup([
              dbc.Label('NGP:'),
              dbc.InputGroup([
                dbc.Input(
                  type='number', 
                  id='ngp-hr',
                  min=0, max=23,
                  placeholder='HH',
                  value=hours,
                ),
                dbc.InputGroupAddon(':'),
                dbc.Input(
                  type='number', 
                  id='ngp-min',
                  min=0, max=59,
                  placeholder='MM',
                  value=mins,
                ),
                dbc.InputGroupAddon(':'),
                dbc.Input(
                  type='number', 
                  id='ngp-sec',
                  min=0, max=59,
                  placeholder='SS',
                  value=secs,
                ),
              ]),
            ]),
          ],
          width=4,
        ),
        dbc.Col(
          [
            dbc.FormGroup([
              dbc.Label('IF:'),
              dbc.Input(
                type='number', 
                id='intensity-factor',
                min=0, max=2, step=0.001,
                placeholder='IF',
                # value=round(intensity_factor, 3),
              )
            ]),
          ],
          width=2,
        ),
        dbc.Col(
          [
            dbc.FormGroup([
              dbc.Label('TSS:'),
              dbc.Input(
                type='number', 
                id='tss',
                min=0, max=1000, step=0.1,
                placeholder='TSS',
                # value=round(tss, 1),
              )
            ]),
          ],
          width=2,
        ),
      ]),
      html.Hr(),
    ])

    return stats_div

  @app.callback(
    Output('intensity-factor', 'value'),
    Input('ngp-hr', 'value'),
    Input('ngp-min', 'value'),
    Input('ngp-sec', 'value'),
    Input('cp-min', 'value'),
    Input('cp-sec', 'value')
  )
  def update_intensity_factor(ngp_hr, ngp_min, ngp_sec, cp_min, cp_sec):
    if ngp_min is None or cp_min is None:
      raise PreventUpdate

    ngp_hr = ngp_hr or 0
    ngp_sec = ngp_sec or 0
    cp_sec = cp_sec or 0

    ngp_secs_per_mile = ngp_hr * 3600 + ngp_min * 60 + ngp_sec
    cp_secs_per_mile = cp_min * 60 + cp_sec

    intensity_factor = cp_secs_per_mile / ngp_secs_per_mile
    
    return round(intensity_factor, 3)

  @app.callback(
    Output('tss', 'value'),
    Input('intensity-factor', 'value'),
    State('moving-table', 'data'),
  )
  def update_tss(intensity_factor, table_records):
    if intensity_factor is None:
      raise PreventUpdate

    df_stats = pd.DataFrame.from_records(table_records)
    df_stats.index = df_stats['']

    # This is TP uses 110...not me!
    tss_per_cp_hr = 100
    tss = (tss_per_cp_hr / 3600) * df_stats.loc['Total', 'Time (s)']  \
          * intensity_factor ** 2

    return round(tss, 1)


def calc_stats_df(df):
  """Calculate summary stats and generate a table."""

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
    df_stats['Pace'] = df_stats['Speed (m/s)'].apply(util.speed_to_pace)
    df_stats['Time'] = df_stats['Time (s)'].apply(util.seconds_to_string)
    df_stats['Distance (mi)'] = df_stats['Distance (m)'].astype('float') / util.M_PER_MI

    return df_stats


def create_moving_table(df_stats):
  df_stats.insert(0, '', df_stats.index)
  
  return dash_table.DataTable(
    data=df_stats.to_dict('records'),
    columns=create_moving_table_cols(df_stats.columns),
    id='moving-table'
  )


def create_moving_table_cols(cols):
  return [
    {'name': i, 'id': i, 'type': 'numeric', 'format': {'specifier': '.2f'}}
    if (i.startswith('Distance') or i.startswith('Speed')) else
    {'name': i, 'id': i}
    for i in cols
  ]

  # return dbc.Table.from_dataframe(
  #   # df_stats.loc[['Time', 'Distance (mi)', 'Pace']],
  #   df_stats,
  #   bordered=True
  # )

def create_power_table(df):
  pass
  # if df.fld.has('power'):
  #   from application.power import util as putil

  #   # Calculate Normalized Power using the EWMA-averaged time series.
  #   np = putil.lactate_norm(df['power'])

  #   # Compare effect of throwing out values that occurred before a
  #   # steady-state O2 consumption was likely obtained (parallel to
  #   # TrainingPeaks Normalized Power calculation below).
  #   np_ss = putil.lactate_norm(df['power'][df['time'] > 29])

  #   # TrainingPeaks Normalized Power uses a 30-second moving average.
  #   window = 30  # seconds
  #   power_tp = putil.sma(
  #     df['power_inst'], 
  #     window,
  #     time_series=df['time']
  #   )
  #   # TP throws out the first 30 seconds of data, before the moving
  #   # average reaches full strength.
  #   np_tp = putil.lactate_norm(power_tp[df['time'] > window - 1])

  #   # Mean power for comparison to all averaging techniques.
  #   mean_power = df['power_inst'].mean()
    
  #   table_header = html.Thead(html.Tr([
  #     # html.Th(),
  #     # Make a NP row, colspan=3
  #     html.Th('NP (SMA S-S)'),
  #     html.Th('NP (EWMA S-S)'),
  #     html.Th('NP (EWMA)'),
  #     html.Th('Mean Power')
  #   ]))

  #   table_body = html.Tbody([
  #     html.Tr([
  #       # html.Td('Power'),
  #       html.Td(f'{np_tp:.2f}'),
  #       html.Td(f'{np_ss:.2f}'),
  #       html.Td(f'{np:.2f}'),
  #       html.Td(f'{mean_power:.2f}'),
  #     ])
  #   ])

  #   return dbc.Table([table_header, table_body], bordered=True)


def init_figure_callbacks(app):

  @app.callback(
    Output('plot-options', 'children'),
    Input('activity-data', 'data'),
  )
  def create_plot_opts(record_data):
    if record_data is None:
      raise PreventUpdate

    df = pd.DataFrame.from_records(record_data)

    # Provide a list of x-axis options, with records included by default.
    x_stream_opts = ['record']
    for x in ['time', 'distance']:
      if x in df.columns:
        x_stream_opts.append(x)

    available_figs = []
    # Determine which figures are available based on DataFrame columns. 
    # 'map', 'elevation', 'speed' (, 'power')
    if df.fld.has(LAT, LON):
      available_figs.append(MAP_ID)
    if df.fld.has(ELEVATION) or df.fld.has(GRADE):
      available_figs.append(ELEVATION_ID)
    if df.fld.has(SPEED) or df.fld.has(HEARTRATE) or df.fld.has(POWER):
      available_figs.append(SPEED_ID)

    # TODO: Now we know which figures are available - feed them into a
    # new function that initializes all the hovers based on available
    # figs. (Not working to define callback-in-a-callback rn)
    # https://community.plotly.com/t/dynamic-controls-and-dynamic-output-components/5519
    # init_hover_callbacks_smart(app, available_figs)

    return [
      dbc.Col(
        layout.create_x_stream_radiogroup(x_stream_opts),
      ),
      dbc.Col(
        layout.create_plot_checkgroup(available_figs)
        # layout.create_plot_checkgroup([MAP_ID, ELEVATION_ID, SPEED_ID])
      ),
    ]

  @app.callback(
    Output('figures', 'children'),
    Input('x-selector', 'value'),
    # Input('plot-checklist', 'values'),
    State('activity-data', 'data'),
  )
  def update_figures(x_stream, record_data):
    if record_data is None:
      raise PreventUpdate

    df = pd.DataFrame.from_records(record_data)

    if x_stream == 'record':
      x_stream = None

    return create_rows(df, x_stream_label=x_stream)

  # TODO: Define these callbacks dynamically dammit!
  init_hover_callbacks_smart(app, [MAP_ID, ELEVATION_ID, SPEED_ID])


def create_rows(df, x_stream_label=None):
  """Catch-all controller function for dashboard layout logic.

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
  plotter = Plotter(df)

  if x_stream_label is not None:
    plotter.set_x_stream_label(x_stream_label)

  # *** Row 1: Map ***

  # Check if there are both `lat` and `lon` streams, and create a map
  # if so.
  if df.fld.has(LAT, LON): 
    plotter.init_map_fig(MAP_ID)
  
    plotter.add_map_trace(MAP_ID, lat_label=LAT, lon_label=LON,
      # map trace kwargs here, if desired.
    )

  # *** End of Row 1 (map) ***

  # *** Row 2 (elevation and speed graphs) ***

  if df.fld.has(ELEVATION):

    plotter.init_xy_fig(ELEVATION_ID, new_row=True)

    plotter.add_yaxis(ELEVATION_ID, ELEVATION, **AXIS_LAYOUT[ELEVATION])

    # Add trace to the `elevation` figure, on the default yaxis.
    plotter.add_trace(ELEVATION_ID, ELEVATION,
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

    speed_text = df[SPEED].apply(util.speed_to_pace)
    plotter.add_trace(SPEED_ID, SPEED,
      text=speed_text, 
      visible=True,
      **TRACE_LAYOUT[SPEED]
    )

    if df.fld.has(GRADE):
      # spd_axis = plotter.get_yaxis(SPEED_ID, POWER)
      for stream in ['equiv_speed', 'GAP', 'NGP']:
        plotter.add_trace(SPEED_ID, stream,
          text=df[stream].apply(util.speed_to_pace), 
          visible=True,
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
      **TRACE_LAYOUT[CADENCE]
    )

  # NEW power and flat-ground speed traces.
  if df.fld.has(POWER):
    plotter.add_yaxis(SPEED_ID, POWER, **AXIS_LAYOUT[POWER])
    pwr_axis = plotter.get_yaxis(SPEED_ID, POWER)

    plotter.add_trace(SPEED_ID, POWER,
      yaxis=pwr_axis,
      **TRACE_LAYOUT[POWER]
    )

  # Draw rectangles on the speed figure for strava stopped periods.
  # TODO: Make this into its own function, I think.
  
  if df.fld.has('moving') and plotter.has_fig(SPEED_ID):
    # Highlight stopped periods on the speed plot with rectangles.

    # Find all the timestamps when strava switches the user from stopped
    # to moving, or from moving to stopped.
    stopped_ixs = df.index[~df['moving']]
    stopped_periods_start_ixs = stopped_ixs[
      stopped_ixs.to_series().diff() != 1]
    stopped_periods_end_ixs = stopped_ixs[
      stopped_ixs.to_series().diff(-1) != -1]

    fig_with_stops = plotter.get_fig_by_id(SPEED_ID)

    for i in range(len(stopped_periods_start_ixs)):
      start_ix = stopped_periods_start_ixs[i]
      end_ix = stopped_periods_end_ixs[i]

      if start_ix == end_ix:
        # A single point - use a line, not a rectangle.
        fig_with_stops.add_vline(
          # x=df['time'][start_ix],
          x=plotter.x_stream[start_ix],
          line_color='red',
          opacity=0.5,
        )
      else:
        fig_with_stops.add_vrect(
          # x0=df['time'][start_ix],
          # x1=df['time'][end_ix],
          x0=plotter.x_stream[start_ix],
          x1=plotter.x_stream[end_ix],
          #layer='below',
          #line={'width': 0}, 
          line_color='red',
          #fillcolor='LightSalmon',
          fillcolor='red',
          opacity=0.5,
        )

  # *** End of row 2 (elevation and speed) ***

  return plotter.rows


def init_hover_callbacks_smart(app, available_figs):
  for fig_id_from in available_figs:
    for fig_id_to in available_figs:
      if fig_id_to == MAP_ID:
        # Mapbox traces appear on a non-default subplot.
        # There should be only one valid curve on the map for now.
        init_callback_force_hover(app, fig_id_from, fig_id_to, subplot_name='mapbox')
      else:
        # We don't know how many curves will need to be hovered, but since
        # it is just the xy plot, we can hover as many curves as we want.
        # (The map, on the other hand, might have some funky traces with
        # a different number of points.)
        init_callback_force_hover(app, fig_id_from, fig_id_to, num_curves=10)


def init_callback_force_hover(
  app,
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

  app.clientside_callback(
    force_hover_script_template.format(to_id, num_curves, subplot_name),
    # Can use any 'data-*' wildcard property, and they
    # must be unique for each graph to hover.
    Output('{}_dummy'.format(from_id), 'data-{}'.format(to_id)),
    [Input(from_id, 'hoverData')],
  )


# Turn on to enable enhanced schtuff.
# from application.plotlydash.dashboard_activity_next import (
#   create_rows,
#   init_hover_callbacks,
#   update_figures_from_strava
# )