import os

from flask import current_app


def cast_bool_from_str(value):
  """
  https://github.com/heartexlabs/label-studio/blob/4ab452a52f3febe6ea5e2596ddb9768f53f383e0/label_studio/core/utils/params.py#L5
  """
  vals_true = ['true', 't', 'on', '1', 'yes']
  vals_false = ['false', 'f', 'off', '0', 'no', 'not', 'none']
  if isinstance(value, str):
    if value.lower() in vals_true:
      value = True
    elif value.lower() in vals_false:
      value = False
    else:
      raise ValueError(f'Incorrect bool value "{value}". '
                       f'Valid true strings: {vals_true}'
                       f'Valid false strings: {vals_false}')
    return value
  


def get_env(name, default=None, is_bool=False):
  """
  https://github.com/heartexlabs/label-studio/blob/develop/label_studio/core/utils/params.py#L110

  envvar that DF currently looks for:
    * DISTILLINGFLASK_SERVER_URL
    * DISTILLING_FLASK_LOCAL_FILES_DOCUMENT_ROOT
    * STRAVA_CLIENT_ID
    * STRAVA_CLIENT_SECRET
    * STRAVALIB_CLIENT (change to STRAVA_API_CLIENT or st non-stravalib)
    * MOCK_STRAVALIB_ACTIVITY_COUNT
                     SHORT_LIMIT
                     LONG_LIMIT
                     SHORT_USAGE
                     LONG_USAGE
    * FEATURE_FLAGS (TBD)
    * (deprecated) PASSWORD

    * DATABASE_URL (-> SQLALCHEMY_DATABASE_URI)
    * REDIS_URL
    * CELERY_BROKER_URL
  """
  for env_key in ['DISTILLING__FLASK_' + name, 'DISTILLINGFLASK_' + name, name]:
    value = os.getenv(env_key)
    if value is not None:
      if is_bool:
        return cast_bool_from_str(value)
      else:
        return value
  return default


def get_bool_env(key, default):
    return get_env(key, default, is_bool=True)


def flag_set(feature_flag):
  """
  Use this method to check whether this flag is set ON in the current app,
  to split the logic on backend.

  For example,
  ```
  if flag_set('ff-dev-123-some-fixed-issue-231221-short'):
      run_new_code()
  else:
      run_old_code()
  ```
  """
  env_value = get_bool_env(feature_flag, default=None)
  if env_value is not None:
    return env_value
  # fflags = current_app.config.get('FEATURE_FLAGS', {})
  # return fflags.get(feature_flag, False)

def all_flags():
  pass

def get_feature_file_path():
  pass