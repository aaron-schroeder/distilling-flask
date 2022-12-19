"""Core Flask app routes."""
from flask import Blueprint, redirect, render_template
from flask_login import logout_user, login_required

from application.models import Activity


route_blueprint = Blueprint('route_blueprint', __name__)


@route_blueprint.route('/admin')
@login_required
def admin_landing():
  return render_template('admin.html')


@route_blueprint.route('/view-saved-activities')
def view_activities():
  """A simple html list for debugging."""

  return render_template(
    'activities_saved.html',
    activities=Activity.query.all(),
    # title='Show Activities'
  )


@route_blueprint.route('/logout')
def logout():
  logout_user()
  return redirect('/')
