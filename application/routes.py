"""Core Flask app routes."""
import dash
from flask import Blueprint, redirect, render_template
from flask_login import current_user

from application.models import Activity


route_blueprint = Blueprint('route_blueprint', __name__)


@route_blueprint.route('/admin')
def admin_landing():
  if not current_user.is_authenticated:
    return redirect(dash.page_registry['pages.login']['relative_path'])

  return render_template('admin.html')


@route_blueprint.route('/view-saved-activities')
def view_activities():
  """A simple html list for debugging."""

  return render_template(
    'activities_saved.html',
    activities=Activity.query.all(),
    # title='Show Activities'
  )
