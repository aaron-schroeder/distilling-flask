import os

# from dotenv import load_dotenv


# BASEDIR = os.path.abspath(os.path.dirname(__file__))
# load_dotenv(os.path.join(BASEDIR, '.env'))


class Config:
  """Set Flask configuration variables.

  Set by `app.config.from_object(config.Config)`
  
  https://flask.palletsprojects.com/en/2.2.x/config/
  """

  SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
  
  # Deprecated:
  # https://flask.palletsprojects.com/en/2.2.x/config/#ENV
  # ENV = 'development'  
  
  # Prefer --debug arg? Or envvar?
  DEBUG = True

  FLASK_APP = 'application'

  path = os.path.dirname( os.path.realpath(__file__) )
  database_path = os.path.join(path, 'mydb.sqlite')
  SQLALCHEMY_DATABASE_URI = os.environ.get(
    'DATABASE_URL',
    f'sqlite:///{database_path}'
  )

  SQLALCHEMY_ECHO = True
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  CELERY_BROKER_URL = 'redis://localhost:6379/0'
  # CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

  STRAVALIB_CLIENT = os.environ.get('STRAVALIB_CLIENT', 'stravalib.Client')


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
  SECRET_KEY = 'super secret key'


class DummyConfig(Config):
  SQLALCHEMY_DATABASE_URI = 'sqlite:///dummy.db'
  # STRAVA_API_BACKEND = 'application.util.mock_stravalib.Client'
  # STRAVA_API_BACKEND = 'application.util.mock_stravalib.LowLimitClient'
  # STRAVA_API_BACKEND = 'application.util.mock_stravalib.SimProdClient'

  STRAVALIB_CLIENT = 'application.util.mock_stravalib.Client'
  MOCK_STRAVALIB_ACTIVITY_COUNT = 100
  MOCK_STRAVALIB_SHORT_LIMIT = 100
  MOCK_STRAVALIB_LONG_LIMIT = 1000
  MOCK_STRAVALIB_SHORT_USAGE = 0
  MOCK_STRAVALIB_LONG_USAGE = 0


class ProductionConfig(Config):
  DEBUG = False  # just in case
  SECRET_KEY = os.environ.get('SECRET_KEY') # don't set a default value

  user = os.environ.get('POSTGRES_USER')
  pw = os.environ.get('POSTGRES_PW')
  
  db_url = os.environ.get('POSTGRES_URL')
  port = os.environ.get('POSTGRES_PORT')
  
  db = os.environ.get('POSTGRES_DB')

  if (user and pw and db_url and db):
    SQLALCHEMY_DATABASE_URI = f'postgresql+psycopg2://{user}:{pw}@{db_url}/{db}'
  
  # if (user and pw and db_url and port and db):
  #   SQLALCHEMY_DATABASE_URI = f'postgresql+psycopg2://{user}:{pw}@{db_url}:{port}/{db}'
  
  # Otherwise use default sqlite config


config = {
  'dev': Config,
  'test': TestingConfig,
  'dummy': DummyConfig,
  'prod': ProductionConfig
}
