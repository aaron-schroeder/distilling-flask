import os

import dash
from flask import redirect, render_template, request, Response, session, url_for
from flask_login import current_user, login_required

from . import strava_api
from application.models import db, StravaAccount
from application import stravatalk


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


@strava_api.route('/authorize')
@login_required
def authorize():

  return redirect(
    f'https://www.strava.com/oauth/authorize?'  
    f'client_id={CLIENT_ID}&redirect_uri=http://localhost:5000/'
    f'{url_for("strava_api.handle_code")}&approval_prompt=auto'
    '&response_type=code&scope=activity:read_all'
  )


@strava_api.route('/callback')
@login_required
def handle_code():

  if request.args.get('error', None) is not None:
    # Handles user clicking "cancel" button, resulting in a response like:
    # http://localhost:5000/strava/redirect?state=&error=access_denied
    error = (
      'It looks like you clicked "cancel" on the strava permission screen.\n'
      'If you want to use Training Zealot to analyze your Strava data, '
      'you must grant the app access to your Strava data.\n'
      f'Error from Strava API: {request.args.get("error")}'
    )
    return render_template(
      'strava_api/callback.html',
      error=error
    )

  # Validate that the user accepted the necessary scope,
  # and display a warning if not.
  scope = request.args.get('scope')
  if 'activity:read_all' not in scope.split(','):
    error = (
      'You did not accept the required permission '
      '"View data about your private activities"\n'
      'If you want to use Training Zealot to analyze your Strava data, '
      'you must accept all permissions.'
    )
    return render_template(
      'strava_api/callback.html',
      error=error
    )

  token = stravatalk.get_token(
    request.args.get('code'),
    CLIENT_ID, 
    CLIENT_SECRET
  )

  strava_acct = StravaAccount(
    strava_id=token['athlete']['id'],
    access_token=token['access_token'],
    refresh_token=token['refresh_token'],
    expires_at=token['expires_at'],
    # _=token['athlete']['firstname'],
    # _=token['athlete']['lastname'],
    # _=token['athlete']['profile_medium'],
    # _=token['athlete']['profile'],
  )
  db.session.add(strava_acct)
  db.session.commit()

  # Redirect them to the main admin
  return redirect(url_for('route_blueprint.admin_landing'))

  # # Redirect them to an activity list that uses the session data
  # return redirect(url_for('strava_api.display_activity_list'))


@strava_api.route('/activities')
@login_required
def display_activity_list():
  """Display list of strava activities to view in their own Dashboard."""
  if not current_user.has_authorized:
    return redirect(url_for('strava_api.authorize'))
    # '?after="/strava/activities"'

  token = current_user.strava_account.get_token()

  activity_json = stravatalk.get_activities_json(
    token['access_token'],
    page=request.args.get('page')
  )

  return render_template(
    'strava_api/activity_list.html',
    resp_json=activity_json
  )

@strava_api.route('/revoke')
@login_required
def revoke():
  if current_user.has_authorized:
    db.session.delete(current_user.strava_account)
  db.session.commit()

  return redirect(url_for('route_blueprint.admin_landing'))
