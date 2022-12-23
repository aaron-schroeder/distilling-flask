import os
import dash
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


from application.config import config


db = SQLAlchemy()
login = LoginManager()


def create_app(config_name='dev'):
  """Construct core Flask application with embedded Dash apps.

  The application factory function. Flask auto-detects `create_app`
  and `make_app`.
  https://flask.palletsprojects.com/en/1.1.x/patterns/appfactories/
  """
  app = Flask(__name__, instance_relative_config=True)

  app.config.from_object(config[config_name])

  # ensure the instance folder exists
  # TODO: Figure out if I need this at all.
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass

  # SQLAlchemy
  db.init_app(app)

  from application.routes import route_blueprint
  app.register_blueprint(route_blueprint)

  from application.strava_api import strava_api as strava_api_blueprint
  app.register_blueprint(strava_api_blueprint, url_prefix='/strava')

  with app.app_context():
    # Add various dashboards using this Flask app as a server.
    from application.plotlydash.app import add_dashboard_to_flask
    add_dashboard_to_flask(app)
    
    # SQLAlchemy
    from application import models
    # temporary - start with a fresh db since I haven't got migrations
    # set up yet.
    # db.drop_all()
    
    db.create_all()  # Create sql tables for our data models

  # Flask-Login
  login.init_app(app)
  login.login_view = dash.page_registry['pages.login']['relative_path']

  return app
