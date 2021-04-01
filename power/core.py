"""Everything related to O2 power. Hoooo baby."""

import math

import numpy as np
import pandas as pd

from . import util


def o2_power_ss(speed_series, grade_series=None):
  """Calculates steady-state oxygen consumption in the moderate domain.

  For more info, see `heartandsole_local/heartandsole/powerutils.py`.
  """
  if grade_series is None:
    grade_series = pd.Series([0 for i in range(len(speed_series))])

  c_i_series = grade_series.apply(cost_of_inclined_treadmill_running)

  c_aero_series = speed_series.apply(cost_of_wind_running)

  # Combine the two components that contribute to the metabolic cost of
  # running.
  c_r_series = c_i_series + c_aero_series

  # Instantaneous running power (W/kg) is simply cost of running 
  # (J/kg/m) multiplied by speed (m/s).
  power_series = (c_i_series + c_aero_series) * speed_series
  
  # Updated to account for the fact that the horizontal speed is
  # measured, but cost of running relates to the distance along the
  # incline.
  power_series = power_series / np.cos(np.arctan(grade_series))

  return power_series


def o2_power(speed_series, grade_series=None, time_series=None, tau=20):
  """Calculate O2 consumption in the moderate domain as a time series.

  Args:
    tau: Time constant for the exponentially-weighted moving average.
      According to (Poole and Jones, 2012), this constant can vary from
      10s to over 100s. It decreases with training, reflecting a more
      responsive cardiovascular system. Default 20.

  Note: 
    * In the heavy domain, the slow component of O2 consumption
      kicks in, steady-state O2 consumption is higher than predicted
      by this algorithm, and the steady state does not occur for up
      to 20 minutes (longer than this algorithm predicts.)
    * In the severe domain, the critical power has been exceeded,
      and O2 consumption will reach VO2 max. The slow component
      may play a role, but this role diminishes as the work rate
      increases. In the extreme case, VO2max is barely
      reached before fatigue sets in - slow component likely
      has no role in oxygen kinetics here.
    * In the extreme (?) domain, the work rate is so high that
      fatigue sets in before VO2max can be attained.

  """
  if time_series is None:
    time_series = pd.Series([i for i in range(len(speed_series))])

  # Calculate the theoretical steady-state power associated with the
  # speed and grade value at each timestep.
  power_inst = o2_power_ss(speed_series, grade_series=grade_series)

  halflife = tau * math.log(2)

  # Even if we have uniform 1-second samples, I would still need this
  # util function. It makes the average start at 0 and trend up, rather
  # than letting the first value have all the weight.

  return util.ewma(
    power_inst,
    halflife,
    time_series=time_series,
  )
  

def run_power(speed, grade=0.0):
  return run_cost(speed, grade=grade) * speed / math.cos(math.atan(grade))


def run_cost(speed, grade=0.0):
  """Calculates the metabolic cost of running.

  See the documentation for powerutils.o2_power_ss for information
  on the scientific basis for this calculation.

  Args:
    speed (float): Running speed in meters per second. 
    grade (float): Decimal grade, i.e. 45% = 0.45.

  Returns:
    float: Cost of running on an incline in still air, in Joules/kg/m,
      with distance measured along the incline slope.
  """
  # grade = grade or 0.0

  # Use that Minetti curve.
  c_i = cost_of_inclined_treadmill_running(grade)

  # Pugh and Di Prampero tell us the cost of resisting wind.
  c_aero = cost_of_wind_running(speed)

  return c_i + c_aero


def cost_of_inclined_treadmill_running(grade):
  """Calculates the cost of inclined running according to Minetti.

  This is how much metabolic energy it costs (J) to move a unit 
  body mass (kg) a unit distance (m) along a treadmill belt surface
  at a steady-state (after running on this treadmill for 4 minutes).
  This metabolic energy cost is estimated based on the amount of
  oxygen you are consuming, and assumes a specific type of fuel is
  being used (mostly carbohydrate, with a dash of fat, and no protein).
  This gives an estimate of 20.9 kJ of energy per liter of oxygen
  consumed.

  For more info, see `heartandsole_local/heartandsole/powerutils.py`,
  specifically the documentation for `o2_power_tendency`.

  Args:
    grade (float): Decimal grade, i.e. 20% = 0.20.

  Returns:
    float: Cost of running, in Joules/kg/m according to Minetti curve.
  """
  # Clip the grade value so we don't use the curve outside its limits
  # of applicability. 
  # TODO: Find a better way to handle the shittiness of the Minetti
  # curve. Maybe find a way to extrapolate for steeper grades based
  # on an assumed efficiency of lifting/lowering...0.25??
  grade = max(-0.45, min(grade, 0.45))

  # Calculate metabolic cost of running (neglecting air resistance),
  # in Joules per meter traveled per kg of body weight, as a function of
  # decimal grade (on a treadmill, technically). From (Minetti, 2002).
  # Valid for grades shallower than 45% (0.45 in decimal form).
  c_i = 155.4 * grade ** 5 - 30.4 * grade ** 4 - 43.3 * grade ** 3  \
    + 46.3 * grade ** 2 + 19.5 * grade + 3.6

  return c_i


def cost_of_wind_running(speed):
  """Calculate metabolic cost of running against wind resistance.
  
  Assumes zero wind speed. From (Pugh, 1971) & (Di Prampero, 1993).
  eta_aero is the efficiency of conversion of metabolic energy into
  mechanical energy when working against a headwind. 

  k is the air friction coefficient, in J s^2 m^-3 kg^-1,
  which makes inherent assumptions about the local air density
  and the runner's projected area and body weight.

  Args:
    speed (float): Running speed in meters per second.

  Returns:
    float: Aerodynamic cost of running, in Joules per meter traveled
    per kg of body weight, as a function
    
  TODO: 
    * Revisit whether 0.5 is an appropriate efficiency value...
      I recall it might have something to do with the speed at which
      the work is being done.
  """
  eta_aero = 0.5
  k = 0.01
  c_aero = k * speed ** 2 / eta_aero

  return c_aero