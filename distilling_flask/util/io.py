import os

from appdirs import user_config_dir, user_data_dir, user_cache_dir


_DIR_APP_NAME = 'distilling-flask'


def get_data_dir():
  data_dir = user_data_dir(appname=_DIR_APP_NAME)
  os.makedirs(data_dir, exist_ok=True)
  return data_dir