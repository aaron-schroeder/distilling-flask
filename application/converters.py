"""Methods to convert data into ready-to-digest DataFrames."""
import pandas as pd


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

def from_tcx(fname):
  from activereader import TcxFileReader
  
  reader = TcxFileReader(fname)

  # Build a DataFrame using only trackpoints (as records).
  # Make sure to name the fields appropriately, so the plotter function
  # will find them.
  initial_time = reader.activity_start_time
  records = [
    {
      'time': int((tp.time - initial_time).total_seconds()),
      'lat': tp.lat,
      'lon': tp.lon,
      'distance': tp.distance_m,
      'elevation': tp.altitude_m,
      'heartrate': tp.hr,
      'speed': tp.speed_ms,
      #'cadence': 2.0 * tp.cadence_rpm,
      'cadence': tp.cadence_rpm,
    } for tp in reader.get_trackpoints()
  ]

  df = pd.DataFrame.from_records(records)

  # Drop any columns that lack data.
  df = df.dropna(axis=1, how='all')

  return df

def from_fit(fname):
  from fitparse import FitFile
  from dateutil import tz

  fit = FitFile(fname)
  df_rec = pd.DataFrame.from_records([msg_rec.get_values() for msg_rec in fit.get_messages('record')])

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
    position_lat='lat',
    position_long='lon',
    altitude='elevation',
    heart_rate='heartrate'
  ))

  # Convert units
  def semicircles_to_degrees(semicircles):
    return semicircles * 180 / 2 ** 31

  df_rec['lat'] = semicircles_to_degrees(df_rec['lat'])
  df_rec['lon'] = semicircles_to_degrees(df_rec['lon'])

  time_init = df_rec['timestamp'].iloc[0]
  df_rec['time'] = (df_rec['timestamp'] - time_init).dt.total_seconds().astype('int')

  df_rec['cadence'] = df_rec['cadence'] * 2

  # Drop BS cols if they are there
  df_rec.drop(
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