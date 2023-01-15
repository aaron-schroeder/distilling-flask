from specialsauce.sources import minetti, strava, trainingpeaks

from application.plotlydash.figure_layout import GRADE, SPEED


def calc_power(df):
  """Add grade-adjusted speed columns to the DataFrame."""
  if df.fld.has(SPEED, GRADE):
    df['equiv_speed'] = df[SPEED] * minetti.cost_of_running(df[GRADE]/100) / minetti.cost_of_running(0.0)
    df['NGP'] = df[SPEED] * trainingpeaks.ngp_speed_factor(df[GRADE]/100)
    df['GAP'] = df[SPEED] * strava.gap_speed_factor(df[GRADE]/100)
