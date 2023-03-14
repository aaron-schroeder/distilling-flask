import pandas as pd


def training_stress_score(ngp, ftp, elapsed_time):
  """
  Args:
    ngp (float): normalized graded pace for the activity in m/s
    ftp (float): functional threshold pace of the athlete
    elapsed_time_s (float): elapsed time in seconds
  """
  return 100.0 * (elapsed_time / 3600) * intensity_factor(ngp, ftp) ** 2


def intensity_factor(ngp, ftp):
  return ngp / ftp


def sma(x_series, window_len, time_series=None):
  """Simple moving average.
  
  Since this is used to replicate TrainingPeaks NP/NGP, I throw out the
  first `window_len` of data (30 sec in their case).
  https://help.trainingpeaks.com/hc/en-us/articles/204071804-Normalized-Power

  I'm really not sure if this means they insert 0 values for the first
  30 seconds, or if they take an average of points after 30 seconds.
  My EWMA function (below) slowly increments until it gets to a
  steady-state - so it is biased to be low for short-duration bouts.
  """

  if time_series is None:
    sma = x_series.rolling(window_len).mean()
  else:
    # Assume we are working with seconds.
    if isinstance(window_len, (int, float)):
      window_len = pd.to_timedelta(window_len, unit='s')
    elif isinstance(window_len, str):
      window_len = pd.to_timedelta(window_len)

    x_series.index = time_series.map(lambda x: pd.to_datetime(x, unit='s'))

    sma = x_series.rolling(window_len).mean()

    sma.index = time_series.index

  return sma


def ewma(x_series, half_life, time_series=None):
  """Exponentially-weighted moving average.
  
  Behaves like O2 consumption - takes a while to reach steady-state
  when starting out.

  Args:
    x_series (pandas.Series): Values to make a EWMA of.
    half_life (int, str, or pandas.timedelta): half-life of the EWMA.
      If int, and time_series is provided, assumed to be integer seconds.
    time_series (pandas.Series): integer seconds from the start of the
      activity. If present, these will be used as coordinates over which
      we take the moving average. Default None.
  """

  # (no longer necessary) Calculate alpha from half-life.
  # alpha = 1 - math.exp(-math.log(2) / half_life)
  # alpha = 1 - math.exp(-1 / tau)

  x_series_pad = pd.concat([pd.Series([0.0]), x_series])

  if time_series is None:
    ewm_pad = x_series_pad.ewm(
      # alpha=(1 - math.exp(-1 / tau)),
      # halflife=(-1.0 * math.log(0.5) * tau),
      halflife=half_life,
      adjust=False,
      ignore_na=True,
    ).mean()

    return ewm_pad[1:]
  else:
    # Assume we are working with seconds.
    if isinstance(half_life, (int, float)):
      half_life = pd.to_timedelta(half_life, unit='s')
    elif isinstance(half_life, str):
      half_life = pd.to_timedelta(half_life)

    # Initialize the moving average so it takes off from 0 and tends
    # toward steady-state.
    num_padding = int(half_life.seconds * 40)
    x_series_pad = pd.Series(
      [0.0 for i in range(num_padding)] + x_series.to_list()
    )
    time_series = time_series - time_series[0]
    time_series_pad = pd.Series(
      [i for i in range(num_padding)] + (time_series + num_padding).to_list(),
    ).apply(pd.to_datetime, unit='s')

    # time_series_pad = pd.concat([
    #   pd.Series([0], dtype='datetime64[s]'),
    #   (time_series + 1).apply(pd.to_datetime, unit='s')
    # ])

    ewm_pad = x_series_pad.ewm(
      # alpha=(1 - math.exp(-1 / tau)),
      # halflife=(-1.0 * math.log(0.5) * tau),
      halflife=half_life,
      times=time_series_pad,
      adjust=False,
      ignore_na=True,
    ).mean()

    ewm = ewm_pad[num_padding:]
    ewm.index = x_series.index

    return ewm


def lactate_norm(series):
  """Calculates lactate norm of a series of data.

  Unlike a simple average, the lactate norm emphasizes higher values
  by raising all values to the 4th power, averaging them, then taking
  the 4th root. Emphasizing higher values is rooted in the fact that
  best-fit curves between VO2 (oxygen consumption) and lactate tend
  to follow a 4th-order relationship.

  """
  return (series ** 4).mean() ** 0.25


def pace_str_to_secs(pace_str):
  """Helper function for reading paces from file."""
  times = [float(t) for t in pace_str.split(':')]
  if len(times) == 3:
    return times[0] * 3600 + times[1] *60 + times[2]
  
  return times[0] * 60 + times[1]