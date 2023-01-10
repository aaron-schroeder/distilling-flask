import os
from urllib.parse import urljoin

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from application.models import db, StravaAccount
from . import strava_api


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


@strava_api.route('/authorize')
@login_required
def authorize():

  server_url = os.environ.get(
    'DISTILLINGFLASK_SERVER_URL',
    'http://localhost:5000'
  )

  return redirect(StravaAccount.get_client().authorization_url(
    CLIENT_ID,
    scope=['activity:read_all'],
    redirect_uri=urljoin(
      server_url,
      url_for('strava_api.handle_code')
    )
  ))


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

  token = StravaAccount.get_client().exchange_code_for_token(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    code=request.args.get('code'),
  )

  athlete = StravaAccount.get_client(access_token=token['access_token']).get_athlete()

  strava_acct = StravaAccount.query.get(athlete.id)

  if strava_acct:
    strava_acct.access_token = token['access_token']
    strava_acct.refresh_token = token['refresh_token']
    strava_acct.expires_at = token['expires_at']
    action = 'updated'
  else:
    strava_acct = StravaAccount(
      strava_id=athlete.id,
      access_token=token['access_token'],
      refresh_token=token['refresh_token'],
      expires_at=token['expires_at'],
      # _=token['athlete']['firstname'],
      # _=token['athlete']['lastname'],
      # _=token['athlete']['profile_medium'],
      # _=token['athlete']['profile'],
    )
    db.session.add(strava_acct)
    action = 'added'

  db.session.commit()

  # Redirect them to the main admin
  flash(f'Strava account for {strava_acct.firstname} {strava_acct.lastname} '
        f'successfully {action}!')
  return redirect(url_for('strava_api.manage'))


@strava_api.route('/manage')
@login_required
def manage():
  return render_template(
    'strava_api/manage.html',
    strava_accounts=StravaAccount.query.all()
  )


@strava_api.route('/revoke')
@login_required
def revoke():
  
  strava_account = StravaAccount.query.get(request.args.get('id'))
  
  if strava_account is None:
    flash(f'No strava account was found with id {request.args.get("id")}')
    return redirect(url_for('strava_api.manage'))

  msg_success = (
    f'Strava account {strava_account.firstname} {strava_account.lastname} '
     'successfully removed!'
  )

  db.session.delete(strava_account)
  db.session.commit()

  flash(msg_success)
  return redirect(url_for('strava_api.manage'))
