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

from application import stravatalk
from application.plotlydash import plots


ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')

MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'
DUMMY_MAP_TO_XY_ID = 'dummy'
DUMMY_XY_TO_MAP_ID = 'dummy_alt'
LOCATION_ID = 'url'


def add_dashboard_to_flask(server):
  """Create a Plotly Dash dashboard with the specified server.

  This is actually used to create a dashboard that piggybacks on a
  Flask app, using that app its server.
  """
  dash_app = Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash-activity/',
    
    # Not yet.
    # external_stylesheets=['/static/css/styles.css'],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    
    # Turn this on to avoid using local scripts.
    #external_scripts=[
    #  'https://cdn.plot.ly/plotly-basic-1.54.3.min.js'
    #],
  )

  # Custom HTML layout
  #dash_app.index_string = html_layout

  create_layout(dash_app)
  #dash_app = create_layout(dash_app)

  # Add a url component for callbacks based on strava activity num.
  dash_app.layout.children.append(
    dcc.Location(id=LOCATION_ID, refresh=False)
  )

  # (The only difference between the dashboards, is that this one
  # reads from a url and then gets data from strava, while the other
  # one reads the strava data from a file.)

  init_callbacks(dash_app)

  return dash_app.server


def create_dash_app(fname_strava_json, **kwargs):
  """Construct single-page Dash app that does not talk to strava.
  
  This is distinct from `create_app` because it returns a Dash app,
  rather than a Flask app with embedded Dash app.

  There is a lot of non-DRY business going on between those two methods.
  Looking to fix that.
  """
  app = Dash(
    __name__,
    
    # Not used right now
    #external_stylesheets=['/static/css/styles.css'],
    
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    
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

  # Load data into an appropriately formatted DataFrame
  with open(fname_strava_json) as json_file:
    activity_json = json.load(json_file)

  # Let's try and break this up into components:

  # --- Reading the file in from json (or whatever format) ---
  # source-specific
  df = from_strava_streams(activity_json)
  #df = df_ops.readers.from_strava_streams(activity_json)

  # --- Cleaning the DataFrame that was read in ---
  # source-specific/agnostic

  # if 'latlng' in df.columns: 
  #   df = df_ops.cleanup_latlng_strava(df) 

  # --- Calculating fields from existing fields ---
  # source-agnostic (pkgs)
  # (This is left up to the user - can be extended)

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
  # (This is based on what is found in the DF - so in a sense, the DF
  # is the method of communication of what shows up on the plot. This
  # begs for a standardized system of naming/tracking fields IMO).
  # (Or could there be some control in the Dash/plotly functions?
  # But what's the point of that - calculating new cols in the DF only
  # to avoid plotting them...do I need that?)

  # Here's how I see it: Dash and plotly work hand-in-hand. Dash app
  # looks for specific fields and makes plots with them, using its
  # own logic.
  # * If there's elevation, it makes that plot, and adds grade if there.
  # * If there's speed, it makes that plot, and adds cadence if there.
  # * If there's power or HR, it makes that plot.

  # Tasks handled include:
  # * creating the layout/divs/graphs in the Dash app
  # * populating the graphs with plotly figures
  # * adding any user-specified geojson/traces to the map fig,
  #   if lat/lon is included
  # * setting up desired callbacks between the graphs

  # The old way:
  # Break this monolithic function up into bite-sized, individually-
  # controllable pieces. At the same time, all the individual functions
  # here require knowledge of how the others operate. So it's like I
  # need to refactor to make these into individual pipelines. Integrate vertically while separating horizontally.
  create_layout(app, df, **kwargs)
  #app = create_layout(app, df)
  
  init_callback_map_to_xy(app)
  init_callback_xy_to_map(app)
  
  return app


def create_layout(dash_app, df=None, **kwargs):  
  
  # Thinking of splitting this into individual functions that handle
  # each component and its callbacks.

  # For now, I'm gonna try and make this function the point player for
  # everything. It will all flow through here.
  
  if df is not None:
    figs = plots.create_xy_plotter_figs(df)

  dash_app.layout = html.Div(
    children=[
      dcc.Graph(
        id=MAP_ID,
        figure=plots.create_map_fig(df, **kwargs) if df is not None else go.Figure(),
        config={'doubleClick': False},
      ),
      html.Div(
        className='row',
        children=[
          dcc.Graph(
            id=ELEVATION_ID,
            figure=figs[ELEVATION_ID] if df is not None else go.Figure(),
            className='col-6',
            clear_on_unhover=True
          ),

          dcc.Graph(
            id=SPEED_ID,
            figure=figs[SPEED_ID] if df is not None else go.Figure(),
            className='col-6',
            clear_on_unhover=True
          ),
          
          # For map-to-XY hover callback
          html.Div(id=DUMMY_MAP_TO_XY_ID),
        ],
      ),

      # # For map-to-XY hover callback
      # html.Div(id=DUMMY_MAP_TO_XY_ID),

      # For athlete_callback_reverse
      html.Div(id=DUMMY_XY_TO_MAP_ID),
    ],
    id='dash-container'
  )

  #return dash_app


def from_strava_streams(stream_list):
  """Processes strava stream list (json) into a DataFrame."""
  stream_dict = {stream['type']: stream['data'] for stream in stream_list}

  df = pd.DataFrame.from_dict(stream_dict)

  df['lat'] = df['latlng'].apply(lambda x: x[0])
  df['lon'] = df['latlng'].apply(lambda x: x[1])
  df = df.drop('latlng', axis=1)

  # Convert RPM to SPM since we are talking about running.
  df['cadence'] = df['cadence'] * 2

  return df


def init_callbacks(dash_app):
  @dash_app.callback(
    [
      Output(MAP_ID, 'figure'),
      Output(ELEVATION_ID, 'figure'),
      Output(SPEED_ID, 'figure'),
    ],
    [Input(LOCATION_ID, 'pathname')]
  )
  def update_figs(pathname):
    """Where all the data-related magic happens."""

    activity_id = os.path.basename(os.path.normpath(pathname))

    stream_list = stravatalk.get_activity_json(activity_id, ACCESS_TOKEN)

    df = from_strava_streams(stream_list)

    map_fig = plots.create_map_fig(df)
    xy_figs = plots.create_xy_plotter_figs(df)

    return(
      map_fig,
      xy_figs[ELEVATION_ID],
      xy_figs[SPEED_ID],
    )

  init_callback_map_to_xy(dash_app)

  init_callback_xy_to_map(dash_app)


def init_callback_map_to_xy(dash_app):
  # Hover on map -> hover on xy graphs.

  script_template = """
    function(hoverData) {{
      var myPlot = document.getElementById('{0}')
      if (!myPlot.children[1]) {{
        return window.dash_clientside.no_update
      }}
      myPlot.children[1].id = '{0}_js'

      if (hoverData) {{
        if (hoverData.points[0].curveNumber > 1) {{
          return window.dash_clientside.no_update
        }}
               
        //var t = hoverData.points[0].pointIndex
        var t = hoverData.points[0].customdata
        //t = Math.round(t*10)/10
        Plotly.Fx.hover('{0}_js', {{xval: t, yval:0}})
      }}
      return window.dash_clientside.no_update
    }}
    """

  dash_app.clientside_callback(
    script_template.format(ELEVATION_ID),
    # Can use any 'data-*' wildcard property, and they
    # must be unique for each graph to hover.
    Output(DUMMY_MAP_TO_XY_ID, 'data-{}'.format(ELEVATION_ID)),
    [Input(MAP_ID, 'hoverData')],
  )

  dash_app.clientside_callback(
    script_template.format(SPEED_ID),
    Output(DUMMY_MAP_TO_XY_ID, 'data-{}'.format(SPEED_ID)),
    [Input(MAP_ID, 'hoverData')],
  )


def init_callback_xy_to_map(dash_app):
  # Hover on xy graph -> hover on map
  dash_app.clientside_callback(
    """
    function(hoverData) {{
      var myPlot = document.getElementById('{0}')

      if (!myPlot.children[1]) {{
        return window.dash_clientside.no_update
      }}
      myPlot.children[1].id = '{0}_js'

      if (hoverData) {{
        // This should be of the form '?-mapbox'
        //var map_uid = document.getElementsByClassName('mapboxgl-map')[0].id;
        //console.log(map_uid);

        var t = hoverData.points[0].pointIndex
        //t = Math.round(t*10)/10
        div = document.getElementById('{0}_js');
        var evt = [
          {{curveNumber:0, pointNumber: t}}, 
          {{curveNumber:1, pointNumber: t}}
        ];
        Plotly.Fx.hover(
          '{0}_js',
          evt,
          'mapbox'
        )
      }}
      return window.dash_clientside.no_update
    }}
    """.format(MAP_ID),
    Output(DUMMY_XY_TO_MAP_ID, 'data-hover'),
    # I GET IT NOW. This provides me with 3 hoverData inputs.
    # The function should work with all 3 as args. Raha.
    [
      Input(ELEVATION_ID, 'hoverData'),
      #Input(SPEED_ID, 'hoverData'),
    ]
  )