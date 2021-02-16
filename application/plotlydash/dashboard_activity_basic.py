import json
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
from application.plotlydash import plots


ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')


def init_layout():
  return html.Div(
    children=[],
    id='dash-container',
    #className='container',
  )


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
    children = plots.create_plotter_rows(df)

    return children

  init_hover_callbacks(dash_app)

  return dash_app.server


def create_dash_app_df(df, source_name):
  """Construct single-page Dash app that does not talk to strava.
  
  This is distinct from `create_app` because it returns a Dash app,
  rather than a Flask app with embedded Dash app.

  There is a lot of non-DRY business going on between those two methods.
  Looking to fix that.
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

  # Let's try and break this up into components:

  # --- Cleaning the DataFrame that was read in ---
  # source-specific/agnostic
  # (done in from_strava_streams)

  # --- Converting the column labels to StreamLabels in order ---
  # --- to track fields arising from different sources        ---
  df.columns = [StreamLabel(col, source_name) for col in df.columns]

  # --- Calculating fields from existing fields ---
  # source-agnostic (pkgs)
  # This is left up to the user - can be extended

  # disp[m] = f(lat[deg], lon[deg])
  # disp_latlon = distance.spherical_earth_plane_displacement(df['lat'], df['lon'])
  # dist_latlon = disp_latlon.cumsum()

  # speed[m/s] = d(d(dist[m])) / d(time[s])
  # df['speed_calc'] = df['distance'].diff() / df['time'].diff()
  # (Then add to speed plot here)

  # speed[m/s] = d(disp[m]) / d(time[s])
  # df['speed_latlon_calc'] = disp_latlon / df['time'].diff()

  # elevation[m] = f(elevation[m][, time[s]]))
  # df['elevation_smooth'] = elevation.time_smooth(df['altitude'])

  # --- Adding flds from addl sources using other flds --- 
  # agnostic (pkgs)

  # --- Generating Dash graphs / plotly figures ---
  # Tasks handled include:
  # * creating the layout/divs/graphs in the Dash app
  # * populating the graphs with plotly figures
  # * adding any user-specified geojson/traces to the map fig,
  #   if lat/lon is included
  # * setting up desired callbacks between the graphs

  app.layout = init_layout()
  app.layout.children = plots.create_plotter_rows(df)
                              # , x_stream_label='time')

  # TODO: Bring this into `plots.create_plotter_rows()`.
  init_hover_callbacks(app)
  
  return app


def create_dash_app_strava(fname_strava_json):
  """Construct single-page Dash app that does not talk to strava."""

  with open(fname_strava_json) as json_file:
    activity_json = json.load(json_file)

  # Load data into an appropriately formatted DataFrame.
  # df = from_strava_streams(activity_json)
  df = converters.from_strava_streams(activity_json)

  app = create_dash_app_df(df, 'strava')

  return app


MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'
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