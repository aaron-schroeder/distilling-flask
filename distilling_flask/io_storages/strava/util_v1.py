from importlib import import_module
import math
import sys

from flask import current_app


def cached_import(module_path, class_name):
  """
  based on `django.utils.module_loading.import_string`
  """
  # Check whether module is loaded and fully initialized.
  if not (
    (module := sys.modules.get(module_path))
    and (spec := getattr(module, "__spec__", None))
    and getattr(spec, "_initializing", False) is False
  ):
    module = import_module(module_path)
  return getattr(module, class_name)


def import_string(dotted_path):
  """
  Import a dotted module path and return the attribute/class designated by the
  last name in the path. Raise ImportError if the import failed.

  based on `django.utils.module_loading.import_string`
  """
  try:
    module_path, class_name = dotted_path.rsplit(".", 1)
  except ValueError as err:
    raise ImportError("%s doesn't look like a module path" % dotted_path) from err

  try:
    return cached_import(module_path, class_name)
  except AttributeError as err:
    raise ImportError(
      f'Module "{module_path}" does not define a '
      '"{class_name}" attribute/class'
    ) from err


def get_client(backend=None, access_token=None):
  """Load a strava connection backend and return an instance of it.

  If backend is None (default), use `config.STRAVALIB_CLIENT`, or
  finally default to stravalib.
  """
  backend = backend or current_app.config.get('STRAVALIB_CLIENT')
  klass = import_string(backend or 'stravalib.Client')
  for cfg_name, cfg_val in current_app.config.items():
    if (
      cfg_name.startswith('MOCK_STRAVALIB_')
      and current_app.config.get(cfg_name)
    ):
      setattr(
        klass,
        cfg_name.split('MOCK_STRAVALIB')[1].lower(),
        cfg_val
      )
  return klass(access_token=access_token)


def est_15_min_rate(strava_client):
  # Whether we are rate-limited or not, we just got current info
  # on the rate limit status.
  rate_limit_status = strava_client.protocol.rate_limiter.rules[0].rate_limits

  # Create groups of activities to be added. 
  # Split into 15-minute waves (because of 15-min limit),
  # but ultimately decide the rate based on the daily limit.
  # (In the future, we can be smarter about which limit will
  # be hit first.)
  rate_hourly_max = min(
    (rate_limit_status['long']['limit'] - 5) / (24 * 3),
    (rate_limit_status['short']['limit']- 5) / (0.25 * 3)
  )
  return math.floor(rate_hourly_max * 0.25)
