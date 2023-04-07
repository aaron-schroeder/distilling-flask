import os
from urllib.parse import urljoin

from flask import flash, redirect, render_template, request, url_for

from distilling_flask import db
from distilling_flask import messages
from distilling_flask.io_storages.strava import strava
from distilling_flask.io_storages.strava.models import StravaImportStorage
from distilling_flask.io_storages.strava.util import StravaOauthClient
from distilling_flask.util.feature_flags import flag_set


CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
OAUTH_CLIENT = StravaOauthClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)


@strava.route('/authorize')
def authorize():
  server_url = request.base_url  # or 'http://localhost:5000'
  params = dict(response_type='code',
                scope='activity:read_all',
                redirect_uri=urljoin(
                  server_url,
                  url_for('strava_api.handle_code')),
                approval_prompt='auto')
  return redirect(OAUTH_CLIENT.build_url('authorize', **params))


@strava.route('/callback')
def handle_code():
  if request.args.get('error') is not None:
    # Handles user clicking "cancel" button, resulting in a response like:
    # http://localhost:5000/strava/redirect?state=&error=access_denied
    return render_template(
      'strava_api/callback_permission.html',
      warning='It looks like you clicked "cancel" on Strava\'s '
              'authorization page. If you want to use distilling-flask '
              'to analyze your Strava data, you must grant the app access.')

  # Validate that the user accepted the necessary scope,
  # and display a warning if not.
  elif 'activity:read_all' not in request.args.get('scope', '').split(','):
    # Handles user un-selecting the required `activity:read_all` permissions.
    return render_template(
      'strava_api/callback_permission.html',
      warning='Please accept the permission '
              '"View data about your private activities" on Strava\'s '
              'authorization page (otherwise, we won\'t be able to access '
              'your data).')

  resp = OAUTH_CLIENT.post('token', code=request.args.get('code'),
                           grant_type='authorization_code')
  data = resp.json()  # could save whole thing as a blob

  if (
    existing_acct := db.session.get(StravaImportStorage, data['athlete']['id'])
  ) is not None:
    # The user had already authorized this strava account.
    # But the action they just took provides us with a fresh token.
    existing_acct.access_token = data['access_token']
    existing_acct.refresh_token = data['refresh_token']
    existing_acct.expires_at = data['expires_at']
    db.session.commit()

    return render_template(
      'strava_api/callback_duplicate.html',
      strava_name=f"{data['athlete']['firstname']} {data['athlete']['lastname']}"
    )

  # This account doesn't exist in our database, so register it.
  new_acct = StravaImportStorage(**{
    ('id' if flag_set('ff_rename') else 'strava_id'): data['athlete']['id'],
    'access_token': data['access_token'],
    'refresh_token': data['refresh_token'],
    'expires_at': data['expires_at'],
    # _=token['athlete']['firstname'],
    # _=token['athlete']['lastname'],
    # _=token['athlete']['profile_medium'],
    # _=token['athlete']['profile'],
  })
  db.session.add(new_acct)
  db.session.commit()

  # Redirect them to the strava account page
  # TODO: Maybe keep this type of user on the callback page too,
  # so they can have options of what to do next:
  # View strava activity list, import all activities form, 
  # (set up webhooks), ...
  # Alternatively, in a perfect world, the user would land on the
  # strava page and there would be a little helpful tour of strava-enabled
  # features.
  flash(f"Strava account for {data['athlete']['firstname']} "
        f"{data['athlete']['lastname']} was successfully linked!",
        category=messages.SUCCESS)
  return redirect('/settings/strava')


@strava.route('/revoke')
def revoke():
  if (
    (id := request.args.get('id'))
    and (storage := db.session.get(StravaImportStorage, id)) is None
  ):
    flash(f'Could not find a linked Strava account with ID #{id}.',
          category=messages.WARNING)
    return redirect('/settings/strava')
  db.session.delete(storage)
  db.session.commit()
  flash(f'Strava account #{id} was unlinked successfully.',
        category=messages.SUCCESS)
  return redirect('/settings/strava')


@strava.route('/status')
def show_strava_status():
  # TODO: Find a way to RL display status without burning through
  # a dummy request every time. I'm thinking it can be a database 
  # or redis entry.
  if flag_set('ff_rename'):
    from distilling_flask.io_storages.strava.util import StravaRateLimitMonitor
    s = db.session.scalars(db.select(StravaImportStorage)).first()
    response = s.get('/athlete')
    monitor = StravaRateLimitMonitor(response)
    # TODO: Finish
  else:
    from stravalib.exc import RateLimitExceeded

    from distilling_flask.util import units
    from distilling_flask.io_storages.strava.util import get_client

    # Doesn't matter whose token I use
    strava_account = StravaImportStorage.query.first()

    if not strava_account:
      return 'No strava accounts are authorized yet', 200

    client = get_client()

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