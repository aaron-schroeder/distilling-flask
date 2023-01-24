"""Core Flask app routes."""
from flask import redirect, render_template
from flask_login import logout_user, login_required

from application.models import AdminUser
from . import main


@main.route('/settings')
@login_required
def settings():
  return render_template(
    'main/settings.html',
    settings=AdminUser().settings
  )


@main.route('/logout')
def logout():
  logout_user()
  return redirect('/')
