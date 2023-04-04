import datetime

from dateutil import tz
import pandas as pd
from specialsauce.sources import minetti, strava, trainingpeaks

from distilling_flask.plotlydash.figure_layout import GRADE, SPEED
from distilling_flask.util.power import training_stress_score


def calc_power(df):
  """Add grade-adjusted speed columns to the DataFrame."""
  if df.fld.has(SPEED, GRADE):
    df['equiv_speed'] = df[SPEED] * minetti.cost_of_running(df[GRADE]/100) / minetti.cost_of_running(0.0)
    df['NGP'] = df[SPEED] * trainingpeaks.ngp_speed_factor(df[GRADE]/100)
    df['GAP'] = df[SPEED] * strava.gap_speed_factor(df[GRADE]/100)


def calc_ctl_atl(df, ftp):
  """Add power-related columns to the DataFrame.
  
  Args:
    df (pandas.DataFrame): each row represents an activity, and each
      column represents a summary statistic. The following columns
      are required:
        - 'recorded': the datetime each activity began
        - 'ngp_ms': normalized graded pace for each activity in m/s
        - 'elapsed_time_s':
    ftp (float): the athlete's functional threshold pace in m/s.

  NOTE: This function currently has the limitation of accepting a single
  unchanging FTP value for the athlete's entire training history.
  """
  # NOTE: Issues arise if there are two 
  # activities with identical 'recorded' values (which are not necessarily
  # unique in the current db schema). 
  # HACK:
  df = df.drop_duplicates(
    subset=[c for c in df.columns if c not in ('id', 'created')],
    ignore_index=True)

  num_days = (df['recorded'].dt.date.max() - df['recorded'].dt.date.min()).days
  recorded_full = []
  for i in range(num_days + 1):
    dt_dummy = df['recorded'].min() + datetime.timedelta(days=i)
    activities_today = df.loc[df.index[df['recorded'].dt.date == dt_dummy.date()], :]
    
    if len(activities_today):
      recorded_full.extend(activities_today['recorded'].to_list())
    else:
      recorded_full.append(dt_dummy)

  # Add a row representing the current time.
  recorded_full.append(pd.Timestamp.now(tz.gettz('America/Denver')))

  if 'tss' not in df.columns:
    df['tss'] = training_stress_score(df['ngp_ms'], ftp, df['elapsed_time_s'])

  df_padded = df.set_index('recorded'
    ).reindex(pd.DatetimeIndex(recorded_full)
    ).fillna({'tss': 0.0})

  # atl_pre = [0.0]
  atl_0 = 0.0
  atl_pre = [atl_0]
  atl_post = [ df_padded['tss'].iloc[0] / 7.0 + atl_0]
  
  # ctl_pre = [0.0]
  ctl_0 = 0.0
  ctl_pre = [ctl_0]
  ctl_post = [ df_padded['tss'].iloc[0] / 42.0 + ctl_0]
  for i in range(1, len(df_padded)):
    delta_t_days = (df_padded.index[i] - df_padded.index[i-1]).total_seconds() / (3600 * 24)
    
    atl_pre.append(
      (atl_pre[i-1] + df_padded['tss'].iloc[i-1] / 7.0) * (6.0 / 7.0) ** delta_t_days
    )
    atl_post.append(
      df_padded['tss'].iloc[i] / 7.0 + atl_post[i-1] * (6.0 / 7.0)  ** delta_t_days
    )
    ctl_pre.append(
      (ctl_pre[i-1] + df_padded['tss'].iloc[i-1] / 42.0) * (41.0 / 42.0) ** delta_t_days
    )
    ctl_post.append(
      df_padded['tss'].iloc[i] / 42.0 + ctl_post[i-1] * (41.0 / 42.0) ** delta_t_days
    )

  df_padded['ATL_pre'] = atl_pre
  df_padded['CTL_pre'] = ctl_pre
  df_padded['ATL_post'] = atl_post
  df_padded['CTL_post'] = ctl_post

  return df_padded.reset_index(names='recorded')