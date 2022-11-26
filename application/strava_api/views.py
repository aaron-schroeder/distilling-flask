import os

from flask import redirect, render_template, request, Response, session, url_for

from . import strava_api
from application import stravatalk


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


@strava_api.route('/authorize')
def authorize():
  return redirect(
    f'https://www.strava.com/oauth/authorize?'  
    f'client_id={CLIENT_ID}&redirect_uri=http://localhost:5000/'
    f'{url_for("strava_api.handle_code")}&approval_prompt=auto'
    '&response_type=code&scope=activity:read_all'
  )


@strava_api.route('/callback')
def handle_code():
  if request.args.get('error', None) is not None:
    # Handles user clicking "cancel" button, resulting in a response like:
    # http://localhost:5000/strava/redirect?state=&error=access_denied
    return Response(
      'If you want to use Training Zealot to analyze your Strava data, '
      'you must grant the app access to your Strava data.\n'
      f'Error from Strava API: {request.args.get("error")}',
      status=200,
    )

  # Validate that the user accepted the necessary scope,
  # and display a warning if not.
  scope = request.args.get('scope')
  if 'activity:read_all' not in scope.split(','):
    return Response(
      'If you want to use Training Zealot to analyze your Strava data, '
      'you must accept all permissions',
      status=200,
    )
    # return render_template(
    #   'strava_errors.html',
    #   scope=scope,
    #   missing_scope='activity:read_all'
    # )

  session['token'] = stravatalk.get_token(
    request.args.get('code'),
    CLIENT_ID, 
    CLIENT_SECRET
  )

  # Redirect them to an activity list that uses the session data
  return redirect(url_for('strava_api.display_activity_list'))


@strava_api.route('/activities')
def display_activity_list():
  """Display list of strava activities to view in their own Dashboard."""
  token = session.get('token', None)
  if token is None:
    return redirect(url_for('strava_api.authorize'))
    # '?after="/strava/activities"'
  token = stravatalk.refresh_token(token)
  session['token'] = token

  activity_json = stravatalk.get_activities_json(
    token['access_token'],
    page=request.args.get('page')
  )

  return render_template(
    'strava_api/activity_list.html',
    resp_json=activity_json,
    athlete=token['athlete']
  )

@strava_api.route('/logout')
def logout():
  session.pop('token')
  return redirect(url_for('strava_api.authorize'))


