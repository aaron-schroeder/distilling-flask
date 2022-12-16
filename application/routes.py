"""Core Flask app routes."""
from flask import Blueprint, render_template

from application.models import Activity


route_blueprint = Blueprint('route_blueprint', __name__)


@route_blueprint.route('/')
def start_dashapp():
  """Route for the landing page of the Flask app."""

  return render_template('landing_page.html')


@route_blueprint.route('/view-saved-activities')
def view_activities():
  """A simple html list for debugging."""

  return render_template(
    'activities_saved.html',
    activities=Activity.query.all(),
    # title='Show Activities'
  )
