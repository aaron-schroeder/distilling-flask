from dash import Dash
import dash_bootstrap_components as dbc

from application.plotlydash.figure_layout import GRADE, SPEED
from application.plotlydash.aio_components import FigureDivAIO, StatsDivAIO


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

  calc_power(df)

  app.layout = dbc.Container(
    [
      StatsDivAIO(df=df, aio_id='df'),
      FigureDivAIO(df=df, aio_id='df'),
    ],
    id='dash-container',
    fluid=True,
  )

  return app


def calc_power(df):
  """Add power-related columns to the DataFrame.
  
  Note: Honestly need to figure out how I handle calcs in general.

  """

  if df.fld.has(SPEED):
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
      
      df['equiv_speed'] = [adjusted_pace.equiv_flat_speed(s, g / 100) for s, g in zip(df[SPEED], df[GRADE])]
      df['NGP'] = [adjusted_pace.ngp(s, g / 100) for s, g in zip(df[SPEED], df[GRADE])]
      df['GAP'] = [adjusted_pace.gap(s, g / 100) for s, g in zip(df[SPEED], df[GRADE])]
      
    # else:
    #   # Flat-ground power.
    #   df['power_inst'] = power.o2_power_ss(df['speed'])
    #   df['power'] = power.o2_power(
    #     df['speed'],
    #     time_series=df['time'],
    #   )


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


# Turn on to enable enhanced schtuff.
# from application.plotlydash.dashboard_activity_next import (
#   create_rows,
#   init_hover_callbacks,
#   update_figures_from_strava
# )