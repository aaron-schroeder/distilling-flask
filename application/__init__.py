import os
#import requests

from flask import Flask, request, abort
from application import config
from application.plotlydash.dashboard_activity_basic import create_dash_app
#from application.plotlydash.dashboard_activity_new import create_dash_app
#from application.plotlydash.dashboard_activity_basic import create_dash_app

#import application.plotlydash.dashboard_activity_new as dashboard
#import application.plotlydash.dashboard_activity_new as dashboard
#import application.plotlydash.dashboard_activity as dashboard


def create_app(test_config=None):
  """Construct core Flask application with embedded Dash app.

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

  with app.app_context():
    from application import routes

    # Not currently using a dashboard to display all activities
    # (This is handled entirely by the flask app in a simple way)
    # from application.plotlydash.dashboard import create_dashboard
    # app = create_dashboard(app)

    #from application.plotlydash.dashboard_activity import add_dashboard_to_flask
    #from application.plotlydash.dashboard_activity_new import add_dashboard_to_flask
    from application.plotlydash.dashboard_activity_basic import add_dashboard_to_flask
    app = add_dashboard_to_flask(app)
    
    #app = dashboard.add_dashboard_to_flask(app)

    return app