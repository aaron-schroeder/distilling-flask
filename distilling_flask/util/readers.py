"""Methods to convert data into easy-to-digest DataFrames."""
import io

import pandas as pd

from distilling_flask.util.feature_flags import flag_set


# Keep these names straight, in one place.
TIME = 'time'
LAT = 'lat'
LON = 'lon'
SPEED = 'speed'
DISTANCE = 'distance'
ELEVATION = 'elevation'
GRADE = 'grade'
CADENCE = 'cadence'
HEARTRATE = 'heartrate'
MOVING = 'moving'
POWER = 'power'


def from_strava_streams(streams):
  """Processes strava stream list (json) into a DataFrame.
  
  Args:
    stream_dict (dict(stravalib.model.Stream)): Strava stream data,
      as returned by `stravalib.Client.get_activity_streams()`.

  """
  if flag_set('ff_rename'):
    stream_data = {s['type']: s['data'] for s in streams}
  else:
    stream_data = {key: stream.data for key, stream in streams.items()}

  # print(streams)
  df = pd.DataFrame(stream_data)

  # Rename streams to standard names if they are there, ignore if not.
  df = df.rename(columns=dict(
    altitude=ELEVATION,
    velocity_smooth=SPEED,
    grade_smooth=GRADE
  ))

  if 'latlng' in df.columns:
    df[LAT] = df['latlng'].apply(lambda x: x[0])
    df[LON] = df['latlng'].apply(lambda x: x[1])
    df = df.drop('latlng', axis=1)

  # Convert RPM to SPM since we are talking about running, not cycling.
  if CADENCE in df.columns:
    df[CADENCE] = df[CADENCE] * 2

  return df


def from_tcx(file_obj):
  """Read a file object representing a .tcx file into a DataFrame.

  Args:
    file_obj(file or file-like object): Any accepted object accepted
      by `lxml.ElementTree.parse`
      https://lxml.de/tutorial.html#the-parse-function
  """
  from activereader import Tcx
  
  reader = Tcx.from_file(file_obj)

  # Build a DataFrame using only trackpoints (as records).
  # Make sure to name the fields appropriately, so the plotter function
  # will find them.
  initial_time = reader.activities[0].start_time or reader.trackpoints[0].time
  records = [
    {
      TIME: int((tp.time - initial_time).total_seconds()),
      LAT: tp.lat,
      LON: tp.lon,
      DISTANCE: tp.distance_m,
      ELEVATION: tp.altitude_m,
      HEARTRATE: tp.hr,
      SPEED: tp.speed_ms,
      #'cadence': 2.0 * tp.cadence_rpm,
      CADENCE: tp.cadence_rpm,
    } for tp in reader.trackpoints
  ]

  df = pd.DataFrame.from_records(records)

  # Convert RPM to SPM since we are talking about running, not cycling.
  df[CADENCE] = df[CADENCE] * 2

  # Drop any columns that lack data.
  df = df.dropna(axis=1, how='all')

  return df


def from_gpx(file_obj):
  """Read a file object representing a .gpx file into a DataFrame.

  Args:
    file_obj(file or file-like object): Any accepted object accepted
      by `lxml.ElementTree.parse`
      https://lxml.de/tutorial.html#the-parse-function
  """
  from activereader import Gpx
  
  reader = Gpx.from_file(file_obj)

  # Build a DataFrame using only trackpoints (as records).
  # Make sure to name the fields appropriately, so the plotter function
  # will find them.
  initial_time = reader.start_time or reader.trackpoints[0].time
  records = [
    {
      TIME: int((tp.time - initial_time).total_seconds()),
      LAT: tp.lat,
      LON: tp.lon,
      # DISTANCE: tp.distance_m,  # not available in gpx
      ELEVATION: tp.altitude_m,
      HEARTRATE: tp.hr,
      # SPEED: tp.speed_ms,  # not available in gpx
      CADENCE: tp.cadence_rpm,
    } for tp in reader.trackpoints
  ]

  df = pd.DataFrame.from_records(records)

  # Convert RPM to SPM since we are talking about running, not cycling.
  df[CADENCE] = df[CADENCE] * 2

  # Drop any columns that lack data.
  df = df.dropna(axis=1, how='all')

  return df


def from_fit(file_obj):
  """Read a file-ish object representing a .fit file into a DataFrame.

  Args:
    file_obj(str, BytesIO, bytes, file contents): Any accepted `fileish`
      object recognized by `fitparse.FitFile`

  """
  from fitparse import FitFile
  from dateutil import tz

  fit = FitFile(file_obj)
  df_rec = pd.DataFrame.from_records([msg_rec.get_values() for msg_rec in fit.get_messages('record')])

  if not df_rec['timestamp'].is_monotonic_increasing or df_rec['timestamp'].duplicated().any():
    print('Something funky is going on with timestamps.')

  df_evt = pd.DataFrame.from_records([msg_evt.get_values() for msg_evt in fit.get_messages('event')])
  if (df_evt['event_type'] == 'start').sum() > 1:
    print('Pauses are present in this file')
  # pause_times = df_evt['timestamp'][df_evt['event'] == 'timer' and df_evt['event_type'] == 'stop_all']
  # print(pause_times)
  # start_times = df_evt['timestamp'][df_evt['event'] == 'timer' and df_evt['event_type'] == 'start']
  # print(start_times)

  # Calculate some things just bc I want to.
  start_time_rec = df_rec['timestamp'].iloc[0]

  #activity_start_time_utc = start_time_rec.replace(tzinfo=tz.tzutc())
  activity_start_time_utc = start_time_rec.to_pydatetime().replace(tzinfo=tz.tzutc())
  tz_local = tz.gettz('US/Denver')
  activity_start_time_local = activity_start_time_utc.astimezone(tz_local)
  # print(activity_start_time_utc)
  # print(activity_start_time_local)

  total_time_rec = (df_rec['timestamp'].iloc[-1] - start_time_rec).total_seconds()
  n_rec = len(df_rec)
  # print(f'Number of records: {n_rec}\n'
  #       f'Total time from timestamps: {total_time_rec + 1}')

  # Rename pesky cols
  df_rec = df_rec.rename(columns=dict(
    position_lat=LAT,
    position_long=LON,
    altitude=ELEVATION,
    heart_rate=HEARTRATE
  ))

  # Convert units
  def semicircles_to_degrees(semicircles):
    return semicircles * 180 / 2 ** 31

  df_rec[LAT] = semicircles_to_degrees(df_rec[LAT])
  df_rec[LON] = semicircles_to_degrees(df_rec[LON])

  time_init = df_rec['timestamp'].iloc[0]
  df_rec[TIME] = (df_rec['timestamp'] - time_init).dt.total_seconds().astype('int')

  df_rec[CADENCE] = df_rec[CADENCE] * 2

  # Drop BS cols if they are there
  df_rec = df_rec.drop(
    columns=[
        'enhanced_speed',
        'enhanced_altitude',
        'timestamp', 
        # Garmin
        'unknown_88',
        # Wahoo
        'battery_soc',
    ], 
    errors='ignore',
  )

  # Drop any columns that lack data.
  df_rec = df_rec.dropna(axis=1, how='all')

  return df_rec