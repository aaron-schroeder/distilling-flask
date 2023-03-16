import os

from celery import Celery
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

import distilling_flask
from distilling_flask.config import config, Config
from distilling_flask import messages


db = SQLAlchemy()
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)
migrate = Migrate()


def create_app(config_name='dev'):
  """Construct core Flask distilling_flask with embedded Dash apps.

  The distilling_flask factory function. Flask auto-detects `create_app`
  and `make_app`.
  https://flask.palletsprojects.com/en/1.1.x/patterns/appfactories/
  """
  app = Flask(__name__)

  app.config.from_object(config[config_name])
  
  if not app.config['SQLALCHEMY_DATABASE_URI']:

    from distilling_flask.util.io import get_data_dir
    
    # Base path for media root and other uploaded files
    BASE_DATA_DIR = get_data_dir()
    # os.makedirs(BASE_DATA_DIR, exist_ok=True)
    # logger.info('=> Database and media directory: %s', BASE_DATA_DIR)

    database_path = os.path.join(BASE_DATA_DIR, 'distilling.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'

  # ensure the instance folder exists
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass

  # SQLAlchemy
  db.init_app(app)

  # Celery
  celery.conf.update(app.config)

  from distilling_flask.main import main as main_blueprint
  app.register_blueprint(main_blueprint)

  from distilling_flask.strava_api import strava_api as strava_api_blueprint
  app.register_blueprint(strava_api_blueprint, url_prefix='/strava')

  with app.app_context():
    # Add various dashboards using this Flask app as a server.
    from distilling_flask.plotlydash.app import add_dash_app_to_flask
    dash_app = add_dash_app_to_flask(app)

    if app.config.get('DEBUG'):
      dash_app.enable_dev_tools(debug=True)
    
    # SQLAlchemy
    from distilling_flask import models

  # Synchronize html imports across flask and dash apps
  @app.context_processor
  def add_dash_imports():
    return dict(
      dash_css=dash_app._generate_css_dist_html(),
      favicon_url = f"{dash_app.get_asset_url(dash_app._favicon)}"
    )

  # flask-migrate
  migrate.init_app(app, db)

  return app
