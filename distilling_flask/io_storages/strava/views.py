import os
from urllib.parse import urljoin

from flask import flash, redirect, render_template, request, url_for
from stravalib.exc import RateLimitExceeded

from distilling_flask import db
from distilling_flask.util import units
from distilling_flask import messages
from distilling_flask.io_storages.strava import strava
from distilling_flask.io_storages.strava.models import StravaImportStorage


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


@strava.route('/authorize')
def authorize():

  server_url = os.environ.get(
    'DISTILLINGFLASK_SERVER_URL',
    'http://localhost:5000'
  )

  return redirect(StravaImportStorage.get_client().authorization_url(
    CLIENT_ID,
    scope=['activity:read_all'],
    redirect_uri=urljoin(
      server_url,
      url_for('strava_api.handle_code')
    )
  ))


@strava.route('/callback')
def handle_code():
  if request.args.get('error') is not None:
    # Handles user clicking "cancel" button, resulting in a response like:
    # http://localhost:5000/strava/redirect?state=&error=access_denied
    return render_template(
      'strava_api/callback_permission.html',
      warning=(
        'It looks like you clicked "cancel" on Strava\'s authorization page. '
        'If you want to use Training Zealot to analyze your Strava data, '
        'you must grant the app access.'
      )
    )

  # Validate that the user accepted the necessary scope,
  # and display a warning if not.
  elif 'activity:read_all' not in request.args.get('scope', '').split(','):
    # Handles user un-selecting the required `activity:read_all` permissions.
    return render_template(
      'strava_api/callback_permission.html',
      warning=(
        'Please accept the permission '
        '"View data about your private activities" on Strava\'s authorization page '
        '(otherwise, we won\'t be able to access your data).'
      )
    )

  token = StravaImportStorage.get_client().exchange_code_for_token(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    code=request.args.get('code'),
  )
  athlete = StravaImportStorage.get_client(access_token=token['access_token']).get_athlete()
  strava_acct = StravaImportStorage.query.get(athlete.id)

  if strava_acct:
    # The user had already authorized this strava account.
    # But the action they just took provides us with a fresh token.
    strava_acct.access_token = token['access_token']
    strava_acct.refresh_token = token['refresh_token']
    strava_acct.expires_at = token['expires_at']
    db.session.commit()

    return render_template(
      'strava_api/callback_duplicate.html',
      strava_name=f'{strava_acct.firstname} {strava_acct.lastname}'
    )

  # This account doesn't exist in our database, so register it.
  strava_acct = StravaImportStorage(
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
  db.session.commit()

  # Redirect them to the strava account page
  # TODO: Maybe keep this type of user on the callback page too,
  # so they can have options of what to do next:
  # View strava activity list, import all activities form, 
  # (set up webhooks), ...
  # Alternatively, in a perfect world, the user would land on the
  # strava page and there would be a little helpful tour of strava-enabled
  # features.
  flash(
    f'Strava account for {strava_acct.firstname} {strava_acct.lastname} '
    f'was successfully linked!',
    category=messages.SUCCESS
  )
  return redirect('/settings/strava')


@strava.route('/revoke')
def revoke():
  
  strava_account = StravaImportStorage.query.get(request.args.get('id'))
  
  if strava_account is None:
    flash(
      f'Could not find a linked Strava account with ID #{request.args.get("id")}.',
      category=messages.WARNING
    )
    return redirect('/settings/strava')

  msg_success = (
    f'Strava account for {strava_account.firstname} {strava_account.lastname} '
     'was unlinked successfully.'
  )

  db.session.delete(strava_account)
  db.session.commit()

  flash(msg_success, category=messages.SUCCESS)
  return redirect('/settings/strava')


@strava.route('/status')
def show_strava_status():
  # Doesn't matter whose token I use
  strava_account = StravaImportStorage.query.first()

  if not strava_account:
    return 'No strava accounts are authorized yet', 200

  client = strava_account.client

  try:
    client.get_athlete()
  except RateLimitExceeded as e:
    result = 'RateLimitExceeded'
  else:
    result = 'Did not throw `RateLimitExceeded`' 
    
  short = client.protocol.rate_limiter.rules[0].rate_limits['short']
  long = client.protocol.rate_limiter.rules[0].rate_limits['long']

  return (
    (
      f'<html>'
      f'  <div>{result}</div>'
      f'  <div>Short: {short["usage"]}/{short["limit"]} in {units.seconds_to_string(short["time"], show_hour=True)}</div>'
      f'  <div>Long: {long["usage"]}/{long["limit"]} in {units.seconds_to_string(long["time"], show_hour=True)}</div>'
      f'</html>'
    ),
    200
  )