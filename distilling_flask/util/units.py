import datetime
import math


# Define conversion factors.
FT_PER_M = 3.28084
M_PER_MI = 1609.34
KG_PER_LB = 2.2



def pace_to_speed(pace_string):
  return M_PER_MI / string_to_seconds(pace_string)
  

def datetime_to_string(dt, show_hour=False):
  if show_hour or dt.hour > 0:
    return dt.strftime('%-H:%M:%S')

  return dt.strftime('%-M:%S')


def speed_to_timedelta(speed_ms):
  if speed_ms is None or isinstance(speed_ms, str):
    return None

  if speed_ms <= 0.1:
    return datetime.timedelta(days=1)

  pace_min_mile = M_PER_MI / (speed_ms * 60.0)
  
  return datetime.timedelta(minutes=pace_min_mile)


def speed_to_pace(speed_ms):
  if speed_ms is None or isinstance(speed_ms, str):
    return None

  if speed_ms <= 0.1:
    return '24:00:00'

  pace_min_mile = M_PER_MI / (speed_ms * 60.0)
  hrs = math.floor(pace_min_mile/60.0), 
  mins = math.floor(pace_min_mile % 60),
  secs = math.floor(pace_min_mile*60.0 % 60)
  mile_pace_time = datetime.time(math.floor(pace_min_mile/60.0), 
                                 math.floor(pace_min_mile % 60),
                                 math.floor(pace_min_mile*60.0 % 60))

  return datetime_to_string(mile_pace_time)


def seconds_to_datetime(seconds):
  if seconds is None:
    return None

  td = datetime.timedelta(seconds=seconds)
  time_zero = datetime.datetime.strptime('0:00', '%H:%M')

  return td + time_zero


def seconds_to_string(seconds, show_hour=False):
  time_dt = seconds_to_datetime(seconds)
  
  return datetime_to_string(time_dt, show_hour=show_hour)


def string_to_seconds(pace_str):
  times = [float(t) for t in pace_str.split(':')]
  
  if len(times) == 3:
    return times[0] * 3600 + 60 * times[1] + times[2]
  
  return 60 * times[0] + times[1]

