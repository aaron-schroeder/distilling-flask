import datetime
import json
import math
import os

from dash import Dash
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import plotly.graph_objs as go

from application.labels import StreamLabel
from application import converters, stravatalk
from application.plotlydash.plots import Plotter


ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')


def add_dashboard_to_flask(server):
  """Create a Plotly Dash dashboard with the specified server.

  This is actually used to create a dashboard that piggybacks on a
  Flask app, using that app its server.
  """
  dash_app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash-activity/',    
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
      # '/static/css/styles.css',  # Not yet.
    ],
  )

  # Initialize an empty layout to be populated with callback data.
  # TODO: Bring this part of layout in here? Plotter can fill it...
  dash_app.layout = init_layout()

  # Use the url of the dash app to retrieve and display strava data.
  dash_app.layout.children.append(
    dcc.Location(id='url', refresh=False)
  )
  @dash_app.callback(
    Output('dash-container', 'children'),
    [Input('url', 'pathname')]
  )
  def update_layout(pathname):
    # Extract the activity id from the url, whatever it is.
    # eg `/whatever/whateverelse/activity_id/` -> `activity_id`
    activity_id = os.path.basename(os.path.normpath(pathname))

    stream_list = stravatalk.get_activity_json(activity_id, ACCESS_TOKEN)

    df = converters.from_strava_streams(stream_list)

    df.columns = [StreamLabel(col, 'strava') for col in df.columns]
    
    return create_rows(df)

  init_hover_callbacks(dash_app)

  return dash_app.server


def create_dash_app(df):
  """Construct single-page Dash app that does not talk to strava.
  
  This is distinct from `create_app` because it returns a Dash app,
  rather than a Flask app with embedded Dash app.
  """
  app = Dash(
    __name__,
    external_stylesheets=[
      dbc.themes.BOOTSTRAP,
      # '/static/css/styles.css',  # Not yet.
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

  app.layout = init_layout()
  app.layout.children = create_rows(df)
                              # , x_stream_label='time')

  # TODO: Consider bringing this into `create_rows()`.
  init_hover_callbacks(app)

  return app


def create_dash_app_df(df, source_name):

  # --- Converting the column labels to StreamLabels in order ---
  # --- to track fields arising from different sources        ---
  # Bring over to converters.py?
  df.columns = [StreamLabel(col, source_name) for col in df.columns]
  app = create_dash_app(df)

  # --- Calculating fields from existing fields ---
  # source-agnostic (pkgs)
  # This is left up to the user - can be extended

  # --- Adding flds from addl sources using other flds --- 
  # agnostic (pkgs)

  # --- Generating Dash graphs / plotly figures ---
  # Tasks handled include:
  # * creating the layout/divs/graphs in the Dash app (plots.py)
  # * populating the graphs with plotly figures (plots.py)
  # * adding any user-specified geojson/traces to the map fig,
  #   if lat/lon is included (upcoming plots.py)
  # * setting up desired callbacks between the graphs (this file)
  
  return app


def create_dash_app_strava(fname_strava_json):
  """Construct single-page Dash app that does not talk to strava."""

  with open(fname_strava_json) as json_file:
    activity_json = json.load(json_file)

  # Load data into an appropriately formatted DataFrame.
  df = converters.from_strava_streams(activity_json)

  app = create_dash_app_df(df, 'strava')

  return app


def init_layout():
  return html.Div(
    children=[],
    id='dash-container',
    #className='container',
  )


MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'


def create_rows(df, x_stream_label=None):
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
  """  
  plotter = Plotter(df)

  if x_stream_label is not None:
    plotter.set_x_stream_label(x_stream_label)

  # *** Row 1: Map ***

  # Check if there are any sources that have both `lat` and `lon`
  # streams, and add all of them to the map.
  lat_srcs = df.columns.sl.field('lat').sl.source_names
  lon_srcs = df.columns.sl.field('lon').sl.source_names
  latlon_srcs = list(set(lat_srcs) & set(lon_srcs))
  
  if len(latlon_srcs) > 0:
    plotter.init_map_fig(MAP_ID)
  
  for latlon_src in latlon_srcs:
    # Start up a map fig, row 1, and don't worry about hovering for now.
    plotter.add_map_trace(MAP_ID, latlon_src,
      # map trace kwargs here.
    )

  # *** End of Row 1 (map) ***

  # *** Row 2 (elevation and speed graphs) ***

  if df.sl.has_field('elevation'):

    # if df.sl.has_field('time'):
    #   plotter.set_x_stream_label('time')
    # else:
    #   plotter.set_x_stream_label('distance')
    #   # TODO: if neither of these x-axes exist, just go by record num.
    #   # I think this means re-writing the x-stream logic...

    plotter.init_xy_fig(ELEVATION_ID, new_row=True)

    # Find the first label with this field.
    elev_labels = df.columns.sl.field('elevation')
    elev_lbl = elev_labels[0]

    plotter.add_yaxis(ELEVATION_ID, 'elevation',
      range=[
        math.floor(df[elev_lbl].min() / 200) * 200,
        math.ceil(df[elev_lbl].max() / 200) * 200
      ],
      ticksuffix=' m',
      hoverformat='.2f',
    )

    # Add matching traces to the `elevation` figure, on the default yaxis.
    for lbl in elev_labels:
      plotter.add_trace(ELEVATION_ID, lbl,
        visible=True
      )
  
  if df.sl.has_field('grade'):

    # Initialize the fig if it hasn't happened already.
    if not plotter.has_fig(ELEVATION_ID):
      plotter.init_xy_fig(ELEVATION_ID, new_row=True)

    plotter.add_yaxis(ELEVATION_ID, 'grade',
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
    grade_axis = plotter.get_yaxis(ELEVATION_ID, 'grade')
    grade_labels = df.columns.sl.field('grade')
    for lbl in grade_labels:
      plotter.add_trace(ELEVATION_ID, lbl,
        yaxis=grade_axis,
        visible=True
      )

  if df.sl.has_field('speed'):
    # TODO: How to handle if there is no elevation plot? We wouldn't 
    # want to be in the same row as the map...I smell a revamp...
    # specify the row we want to live on? For now we can just hack it
    # together.
    new_row = not plotter.has_fig(ELEVATION_ID)
    plotter.init_xy_fig(SPEED_ID, new_row=new_row)

    plotter.add_yaxis(SPEED_ID, 'speed',
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

  speed_labels = df.columns.sl.field('speed')
  for lbl in speed_labels:
    speed_text = df[lbl].apply(speed_to_pace)
    plotter.add_trace(SPEED_ID, lbl,
      yaxis='y1', text=speed_text, visible=True
    )
  
  if df.sl.has_field('heartrate'):

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

    plotter.add_yaxis(SPEED_ID, 'heartrate',
      # Same values no matter if axis is primary or not.
      ticksuffix=' bpm',
      range=[60, 220],
      hoverformat='.0f',
      showticklabels=False,
      showgrid=False,
    )

    # TODO: Consider kwargs to make this call less ambiguous.
    hr_axis = plotter.get_yaxis(SPEED_ID, 'heartrate')
    hr_labels = df.columns.sl.field('heartrate')
    for lbl in hr_labels:
      plotter.add_trace(SPEED_ID, lbl,
        yaxis=hr_axis, 
        line=dict(color='#d62728')
      )

  if df.sl.has_field('cadence'):

    # Initialize the fig if it hasn't happened already.
    if not plotter.has_fig(SPEED_ID):
      # If we have an elevation plot, we stay in the same row.
      # If we don't have an elevation plot, that either means:
      #   - the current row is the map row, and it gets its own row.
      #   - There are no rows yet.
      # In either case, need to start a new row.
      new_row = not plotter.has_fig(ELEVATION_ID)
      plotter.init_xy_fig(SPEED_ID, new_row=new_row)

    plotter.add_yaxis(SPEED_ID, 'cadence',
      # Same values no matter if axis is primary or not.
      ticksuffix=' spm',
      range=[60, 220],
      hoverformat='.0f',
      showticklabels=False,
      showgrid=False,
    )

    # TODO: Consider kwargs to make this call less ambiguous.
    cad_axis = plotter.get_yaxis(SPEED_ID, 'cadence')
    cad_labels = df.columns.sl.field('cadence')
    for lbl in cad_labels:
      # TODO: Specify trace colors, typ, or it'll be up to order of plotting.
      plotter.add_trace(SPEED_ID, lbl,
        yaxis=cad_axis,
        mode='markers',
        marker=dict(size=2)
      )


  # Draw rectangles on the speed figure for strava stopped periods.
  # TODO: Make this into its own function, I think.
  
  if df.sl.has_field('moving') and plotter.has_fig(SPEED_ID):
    # Highlight stopped periods on the speed plot with rectangles.

    # Just pick the first one (hacked together, gross)
    moving_lbl = df.columns.sl.field('moving')[0]
    time_lbl = df.columns.sl.field('time').sl.source(moving_lbl.source_name)[0]

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

    plotter.get_fig_by_id(SPEED_ID).update_layout(dict(shapes=shapes,))

  # *** Row 2 (elevation and speed) ***

  return plotter.rows



FORCE_XY_HOVER_SCRIPT_TEMPLATE = """
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


def init_callback_force_hover(
  dash_app,
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
    dash_app (dash.Dash): The app whose layout elements will receive
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

  dash_app.clientside_callback(
    FORCE_XY_HOVER_SCRIPT_TEMPLATE.format(to_id, num_curves, subplot_name),
    # Can use any 'data-*' wildcard property, and they
    # must be unique for each graph to hover.
    Output('{}_dummy'.format(from_id), 'data-{}'.format(to_id)),
    [Input(from_id, 'hoverData')],
  )


def init_hover_callbacks(dash_app):

  # We don't know how many curves will need to be hovered, but since
  # it is just the xy plot, we can hover as many curves as we want.
  # (The map, on the other hand, might have some funky traces with
  # a different number of points.)
  n = 10
  init_callback_force_hover(dash_app, MAP_ID, ELEVATION_ID, num_curves=n)
  init_callback_force_hover(dash_app, MAP_ID, SPEED_ID, num_curves=n)
  init_callback_force_hover(dash_app, SPEED_ID, ELEVATION_ID, num_curves=n)
  init_callback_force_hover(dash_app, ELEVATION_ID, SPEED_ID, num_curves=n)

  # There should be only one valid curve on the map for now.
  init_callback_force_hover(dash_app, ELEVATION_ID, MAP_ID, subplot_name='mapbox')
  init_callback_force_hover(dash_app, SPEED_ID, MAP_ID, subplot_name='mapbox')