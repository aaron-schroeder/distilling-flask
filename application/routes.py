"""Core Flask app routes."""
import os

from flask import Blueprint, render_template, request

from application import stravatalk
from application.models import Activity


route_blueprint = Blueprint('route_blueprint', __name__)


# (Vestigial) Store the ngrok url we are forwarding to.
# URL_PUBLIC = os.environ.get('URL_PUBLIC')


# Store the strava access token set before running the app.
# This does not work for that:
#session['access_token'] = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')


@route_blueprint.route('/')
def start_dashapp():
  """Route for the landing page of the Flask app."""

  return render_template('landing_page.html')


@route_blueprint.route('/activities')
def display_activity_list():
  """Display list of strava activities to view in Dashboard."""
  #activity_json = stravatalk.get_activities_json(session.get('access_token'))
  activity_json = stravatalk.get_activities_json(
    ACCESS_TOKEN,
    page=request.args.get('page')
  )

  return render_template('activity_list.html', resp_json=activity_json)


@route_blueprint.route('/view-saved-activities')
def view_activities():
  """A simple html list for debugging."""

  return render_template(
    'activities_saved.html',
    activities=Activity.query.all(),
    # title='Show Activities'
  )
