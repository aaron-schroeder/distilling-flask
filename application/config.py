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
  SQLALCHEMY_DATABASE_URI = 'sqlite:///' + database_path

  SQLALCHEMY_ECHO = True
  SQLALCHEMY_TRACK_MODIFICATIONS = False


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


class ProductionConfig(Config):
  DEBUG = False  # just in case
  SECRET_KEY = os.environ.get('SECRET_KEY') # don't set a default value


config = {
  'dev': Config,
  'test': TestingConfig,
  'prod': ProductionConfig
}
