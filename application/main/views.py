"""Core Flask app routes."""
from flask import redirect, render_template
from flask_login import logout_user, login_required

from application.models import Activity
from . import main


@main.route('/admin')
@login_required
def admin_landing():
  return render_template('main/admin.html')


@main.route('/view-saved-activities')
def view_activities():
  """A simple html list for debugging."""

  return render_template(
    'main/activities_saved.html',
    activities=Activity.query.all(),
    # title='Show Activities'
  )


@main.route('/logout')
def logout():
  logout_user()
  return redirect('/')
