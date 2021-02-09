import os

#from dotenv import load_dotenv


# BASEDIR = os.path.abspath(os.path.dirname(__file__))
# load_dotenv(os.path.join(BASEDIR, '.env'))


class Config:
  """Set Flask configuration variables.

  Set by `app.config.from_object(config.Config)`
  
  https://flask.palletsprojects.com/en/1.1.x/config/
  https://flask.palletsprojects.com/en/1.1.x/config/#configuring-from-files
  """

  # General Flask Config: not hidden because I only run dev mode.

  # https://flask.palletsprojects.com/en/1.1.x/config/#SECRET_KEY
  # SECRET_KEY = os.environ.get('SECRET_KEY')
  SECRET_KEY = 'dev'
  
  ENV = 'development'  # auto when FLASK_ENV = 'development'
  DEBUG = True  # auto when FLASK_ENV = 'development'

  # Flask application folder name. No need to hide AFAIK.
  #FLASK_APP = os.environ.get('FLASK_APP')
  FLASK_APP = 'application'

  # FLASK_DEBUG = 1  # likely not needed

  # Strava token - load from environment variable.
  ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')

  # Database
  #SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
  #SQLALCHEMY_ECHO = True
  #SQLALCHEMY_TRACK_MODIFICATIONS = False
