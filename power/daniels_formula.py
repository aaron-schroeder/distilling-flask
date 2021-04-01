import datetime
import math

import scipy.optimize

def oxygen_cost_v(v):
  """Effectively defines Daniels' pace-power relationship.
  
  AKA speed-to-vdot.

  Assumed to be the same for all runners.

  Args:
    v (float): velocity in m/min.
  Returns:
    float: oxygen cost to cover distance in mL/kg/min.
  """
  a1 = 0.182258
  a2 = 0.000104
  c = -4.60

  return a1 * v + a2 * v ** 2 + c


def oxygen_cost(d, t):
  """Oxygen cost to cover a given distance in a given time.

  Args:
    d (float): Distance covered in meters.
    t (float): Time to cover distance in minutes.
  """
  return oxygen_cost_v(d / t)


def drop_dead_intensity(t):
  """Intensity that can be maintained for a given time.
  
  All athletes assumed to exhibit identical behavior. Originally
  based on elite athletes.

  Args:
    t (float): Time to exhaustion in minutes.
  Returns:
    float: maximum sustainable intensity for this time, defined as a
      ratio of max sustainable VO2 to VO2max.
  """
  a1 = 0.2989558
  a2 = 0.1894393
  tau1 = 1 / 0.1932605
  tau2 = 1 / 0.012778
  c = 0.8

  return a1 * math.exp(-t / tau1) + a2 * math.exp(-t / tau2) + c


def vdot_to_speed(vdot):
  """Returns velocity in m/min"""

  def func(vel):
    return oxygen_cost_v(vel) - vdot

  roots = scipy.optimize.fsolve(func, vdot / 0.182258)

  return roots[0]


def predict_time(d, vo2max):
  """d in m, vo2max in mL/kg/min"""

  def func(t):
    """t in minutes"""

    return oxygen_cost(d, t) / drop_dead_intensity(t) - vo2max

  # Provide an initial guess by assuming 6:00 pace (4.5 m/s, 270 m/min).  
  roots = scipy.optimize.fsolve(func, d / 270.0)

  if len(roots) == 0:
    print('No roots found')
    return None

  if len(roots) > 1:
    print('Multiple roots found. Wonder why?')

  return roots[0]


def predict_vo2max(d, t):
  """Predict VO2max based on race performance.
  
  Daniels would say this is not really VO2max, but VDOT. That is why
  I call the quantity 'predicted VO2max'. 
  
  Daniels' formula assumes that:
    * At a given pace, everyone consumes the same amount of oxygen
      per minute per kilogram.
    * For a given time to exhaustion, everyone can sustain the same
      percentage of their VO2max.
    * The race is run perfectly, such that the runner is exhausted
      at the exact moment the race ends.

  For all these reasons, Daniels does not call the result VO2 or VO2max.
  He simply terms his own quantity, VDOT.

  Args:
    d (float): Race distance in meters
    t (float): Finish time in minutes
  Returns:
    float: vo2max in mL/kg/min.
    
  """

  return oxygen_cost(d, t) / drop_dead_intensity(t)
