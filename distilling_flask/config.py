import os

from appdirs import user_config_dir, user_data_dir, user_cache_dir


def get_data_dir():
    data_dir = user_data_dir(appname='distilling_flask')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class Config:
  """Set Flask configuration variables.

  Set by `app.config.from_object(config.Config)`
  
  https://flask.palletsprojects.com/en/2.2.x/config/
  """

  SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
  
  # Deprecated:
  # https://flask.palletsprojects.com/en/2.2.x/config/#ENV
  ENV = 'development'
  
  # Prefer --debug arg? Or envvar?
  DEBUG = True

  FLASK_APP = 'distilling_flask'

  SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
  if not SQLALCHEMY_DATABASE_URI:
      # BASE_DATA_DIR = os.environ.get('BASE_DATA_DIR', get_data_dir())
      BASE_DATA_DIR = get_data_dir()
      SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DATA_DIR, "distilling_flask.sqlite")}'

  SQLALCHEMY_ECHO = True
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  CELERY_BROKER_URL = 'redis://localhost:6379/0'

  STRAVALIB_CLIENT = os.environ.get('STRAVALIB_CLIENT', 'stravalib.Client')

  DISTILLING_FLASK_LOCAL_FILES_DOCUMENT_ROOT = os.environ.get(
    'DISTILLING_FLASK_LOCAL_FILES_DOCUMENT_ROOT'
  )


class TestingConfig(Config):
  """
  Refs:
    https://coddyschool.com/upload/Flask_Web_Development_Developing.pdf#page=97
  """
  TESTING = True
  SQLALCHEMY_DATABASE_URI = os.environ.get(
    'TEST_DATABASE_URL',
    'sqlite://'
  )
  SQLALCHEMY_ECHO = False
  SECRET_KEY = 'super secret key'


class DummyConfig(Config):
  SQLALCHEMY_DATABASE_URI = 'sqlite://'
  # STRAVA_API_BACKEND = 'distilling_flask.util.mock_stravalib.Client'
  # STRAVA_API_BACKEND = 'distilling_flask.util.mock_stravalib.LowLimitClient'
  # STRAVA_API_BACKEND = 'distilling_flask.util.mock_stravalib.SimProdClient'

  STRAVALIB_CLIENT = 'distilling_flask.util.mock_stravalib.Client'
  MOCK_STRAVALIB_ACTIVITY_COUNT = 100
  MOCK_STRAVALIB_SHORT_LIMIT = 100
  MOCK_STRAVALIB_LONG_LIMIT = 1000
  MOCK_STRAVALIB_SHORT_USAGE = 0
  MOCK_STRAVALIB_LONG_USAGE = 0


class ProductionConfig(Config):
  DEBUG = False  # just in case
  ENV = 'production'
  SECRET_KEY = os.environ.get('SECRET_KEY') # don't set a default value


config = {
  'dev': Config,
  'test': TestingConfig,
  'dummy': DummyConfig,
  'prod': ProductionConfig
}
