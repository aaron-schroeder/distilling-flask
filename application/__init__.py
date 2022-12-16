import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


from application import config


db = SQLAlchemy()


def create_app(test_config=None):
  """Construct core Flask application with embedded Dash apps.

  The application factory function. Flask auto-detects `create_app`
  and `make_app`.
  https://flask.palletsprojects.com/en/1.1.x/patterns/appfactories/
  """
  app = Flask(__name__, instance_relative_config=True)

  if test_config is None:
    app.config.from_object(config.Config)
  else:
    app.config.from_mapping(test_config)

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
    db.create_all()  # Create sql tables for our data models

  return app
