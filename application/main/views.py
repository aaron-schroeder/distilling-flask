"""Core Flask app routes."""
from flask import redirect, render_template
from flask_login import logout_user, login_required

from application.models import Activity
from . import main


@main.route('/settings')
@login_required
def settings():
  return render_template('main/settings.html')


@main.route('/logout')
def logout():
  logout_user()
  return redirect('/')
