"""Back-calculating TrainingPeaks Normalized Graded Pace"""

import os

import pandas as pd
from scipy.interpolate import interp1d

from . import util


def factor(grade, source='strava'):
  """Speed-independent factor for adjusting pace based on grade.

  TrainingPeaks: decimal grade is constrained to (-0.25, 0.3), because
  that was the range of grades that yielded reasonable paces in my 
  investigation:
    * 0.45 adjusted 8:00 pace to 0:17 pace.
    * The adjustment factor jumped wildly from -0.26 to -0.27.

  Strava: decimal grade is constrained to (-0.45, 0.45) because that
    was the range of values I investigated. That range coincides with
    the values investigated by Minetti. Strava's GAP is now a HR-based,
    big data-derived quantity, so I don't know how steep the grades are
    where it is reasonable. Elsewhere, I don't think I have seen Strava
    report a grade steeper than 50%, so it is possible that defines its
    range of validity.

  Args:
    grade (float): Decimal grade.
  Returns:
    float: Factor that converts speed to normalized graded speed.
      Greater than 1.0 means working harder than on flat.

  """
  if source.lower() == 'strava':
    adjusted_pace = 'GAP'
    grade = max(-0.45, min(0.45, grade))
  elif source.lower() in ['trainingpeaks', 'tp']:
    adjusted_pace = 'NGP'
    grade = max(-0.25, min(0.3, grade))

  dirname = os.path.abspath(os.path.dirname(__file__))
  csv_path = os.path.join(dirname, 'ngp_gap.csv')
  df = pd.read_csv(csv_path)
  
  for col in ['Pace', 'NGP', 'GAP']:
    df[col] = 1609.34 / df[col].apply(util.pace_str_to_secs)

  # df['factor'] = df['NGP'] / df['Pace']

  factor_fn = interp1d(df['Grade'], df[adjusted_pace] / df['Pace'])

  return factor_fn(grade * 100.0)


def ngp(speed, grade=0.0):
  """Hello"""
  return speed * factor(grade, source='tp')


def gap(speed, grade=0.0):
  return speed * factor(grade, source='strava')


def equiv_flat_speed(speed, grade=0.0):
  from scipy.optimize import fsolve

  from .core import run_power

  # Define the function whose root we wish to find.
  def func_to_minimize(v_flat):
    return run_power(v_flat, 0.0) - run_power(speed, grade)

  # Initialize the solver with a reasonable guess for speed (m/s).
  res = fsolve(func_to_minimize, x0=3.0)

  return res[0]


def power_to_flat_speed(inclined_running_power):
  """Find flat-ground speed with equivalent power.

  Args:
    inclined_running_power (float): O2 consumption (ml/kg/min).

  """
  from scipy.optimize import fsolve

  from .core import run_power

  # Define the function whose root we wish to find.
  def func_to_minimize(v_flat):
    return run_power(v_flat, 0.0) - inclined_running_power

  # Initialize the solver with a reasonable guess for speed (m/s).
  res = fsolve(func_to_minimize, x0=3.0)

  return res[0]