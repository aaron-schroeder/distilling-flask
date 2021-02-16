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
from application import stravatalk
from application.plotlydash import plots


ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')


LOCATION_ID = 'url'


# TODO: Get rid of div ids once they are handled entirely by Plotter.
MAP_ID = 'map'
ELEVATION_ID = 'elevation'
SPEED_ID = 'speed'
DUMMY_MAP_TO_XY_ID = 'map_dummy'


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
    
    # Turn this on to avoid using local scripts.
    #external_scripts=[
    #  'https://cdn.plot.ly/plotly-basic-1.54.3.min.js'
    #],
  )

  init_layout(dash_app)

  # Add a url component for callbacks based on strava activity num.
  dash_app.layout.children.append(
    dcc.Location(id=LOCATION_ID, refresh=False)
  )

  # (The only difference between the dashboards, is that this one
  # reads from a url and then gets data from strava, while the other
  # one reads the strava data from a file.)

  init_callbacks(dash_app)

  return dash_app.server


def create_dash_app_strava(fname_strava_json):
  """Construct single-page Dash app that does not talk to strava."""

  with open(fname_strava_json) as json_file:
    activity_json = json.load(json_file)

  # Load data into an appropriately formatted DataFrame
  # source-specific
  df = from_strava_streams(activity_json)
  #df = converters.from_strava_streams(activity_json)

  app = create_dash_app_df(df, 'strava')

  return app


def create_dash_app_df(df, source_name):
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

  # Let's try and break this up into components:

  # --- Cleaning the DataFrame that was read in ---
  # source-specific/agnostic
  # (done in from_strava_streams)

  # --- Converting the column labels to StreamLabels to track ---
  # --- fields arising from different sources                 ---
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
  # (This is based on what is found in the DF - so in a sense, the DF
  # is the method of communication of what shows up on the plot. This
  # begs to use StreamLabels with standard field names IMO).
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
  # need to refactor to make these into individual pipelines. 
  # Integrate vertically while separating horizontally.
  create_layout(app, df)
  
  init_callback_map_to_xy(app)
  init_callback_xy_to_map(app)
  
  return app


def init_layout(dash_app):
  """Set up the bare bones of the Dash graphs to fill with data later.

  I want this to work minimally, since the figures will be filled in
  later, but I also want to follow DRY.
  """
  dash_app.layout = plots.init_layout()


def create_layout(dash_app, df):
  """Catch-all controller function for populating the dashboard.
  
  This assumes we will be having a map (latlons), elevation graph
  (elevation and/or grade), and speed graph (speed/cadence/HR).

  I really think the individual graphs with their corresponding
  figures should be created together.

  I am starting to think that a Multi-page Dash app might work better
  than a Flask html page that links over to the Dash app which then uses
  the URL to do its thing. Like, this works, but...the Dash app is running
  in the background right? It has to be initialized with nothing, right?
  Idk. I am still just not satisfied with the flow.

  Args:
    df (pd.DataFrame): A DataFrame with StreamLabels for column labels,
      or None, in which case a graph with blank figures will be
      returned.
  """
  
  # Thinking of splitting this into individual functions that handle
  # each component and its callbacks.

  # For now, I'm gonna try and make this function the point player for
  # everything. It will all flow through here.
  
  dash_app.layout = plots.create_plotter_layout(df)  # , x_stream_label='time')

  # TODO: Bring callbacks into `plots.create_plotter_layout()`.


def from_strava_streams(stream_list):
  """Processes strava stream list (json) into a DataFrame."""
  stream_dict = {stream['type']: stream['data'] for stream in stream_list}

  df = pd.DataFrame.from_dict(stream_dict)

  # Rename streams to standard names if they are there, ignore if not.
  df = df.rename(columns=dict(
    altitude='elevation',
    velocity_smooth='speed',
    grade_smooth='grade'
  ))

  df['lat'] = df['latlng'].apply(lambda x: x[0])
  df['lon'] = df['latlng'].apply(lambda x: x[1])
  df = df.drop('latlng', axis=1)

  # Convert RPM to SPM since we are talking about running.
  df['cadence'] = df['cadence'] * 2

  return df


def init_callbacks(dash_app):
  @dash_app.callback(
    Output('dash-container', 'children'),
    [Input(LOCATION_ID, 'pathname')]
  )
  def update_layout(pathname):

    # Extract the activity id from the url, whatever it is.
    # eg `/whatever/whateverelse/activity_id/` -> `activity_id`
    activity_id = os.path.basename(os.path.normpath(pathname))

    stream_list = stravatalk.get_activity_json(activity_id, ACCESS_TOKEN)

    df = from_strava_streams(stream_list)

    df.columns = [StreamLabel(col, 'strava') for col in df.columns]
    layout = plots.create_plotter_layout(df)

    return layout

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
        
        // TODO: Using pointIndex might create issues when there
        // are missing values in ANY array. Customdata is a good
        // fix, but I think we should inject something that has
        // no ambiguity: record number (the row number in the DF).
        // Time sometimes gets wonky (jumping forward or backward),
        // and other fields are sometimes NaN.
        //var ix = hoverData.points[0].pointIndex
        var ix = hoverData.points[0].customdata
        //ix = Math.round(ix * 10) / 10

        // I think I can make this universal...
        Plotly.Fx.hover('{0}_js', {{xval: ix, yval:0}});

        // Forcing the mapbox hover event, for ref.
        // Note: this doesn't work when curveNumber 0
        // is hidden. Sticking with position-based hover.
        // var evt = [
        //   {{curveNumber:0, pointNumber: ix}}, 
        //   //{{curveNumber:1, pointNumber: ix}}
        // ];
        // Plotly.Fx.hover(
        //   '{0}_js',
        //   evt,
        //   // 'mapbox'
        // )

        // Note: Could this script become general by receiving 
        // two inputs? 
        // 1) id of the dcc.Graph (map, elevation, speed)
        // 2) name of the subplot that needs to be hovered
        //    (mapbox, xy, xy2, xy3, etc)
        // Not sure, as the xy hovering works because of the
        // shared hovering. To do curvenumber, I'd need to select
        // each trace's point individually (using customdata=record).
        // Hm. I think I will try this out AFTER this commit, when I
        // Play around with multiple traces on the map.
        // Could change the map's hovering to select
        // all nearby points when one pointNumber is selected.
        // Possible?
        //
        // Ok. Really last thought. I envision synchronizing all
        // hovers not by pointnumber, but by customdata.


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
  """Hover on xy graph -> hover on map

  TODO:
    * dummy divs for every xy plot = synchronize
      hovering between xyplots too.
  """

  script_text = """
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
          //{{curveNumber:1, pointNumber: t}}
        ];
        Plotly.Fx.hover(
          '{0}_js',
          evt,
          'mapbox'
        )
      }}
      return window.dash_clientside.no_update
    }}
    """.format(MAP_ID)

  dash_app.clientside_callback(
    script_text,
    Output(f'{ELEVATION_ID}_dummy', 'data-hover'),
    [Input(ELEVATION_ID, 'hoverData')]
  )

  dash_app.clientside_callback(
    script_text,
    Output(f'{SPEED_ID}_dummy', 'data-hover'),
    [Input(SPEED_ID, 'hoverData')]
  )