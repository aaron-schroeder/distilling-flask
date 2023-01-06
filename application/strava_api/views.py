import datetime
import os
from urllib.parse import urljoin

import dateutil
from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required
import pandas as pd
from scipy.interpolate import interp1d
from sqlalchemy.exc import IntegrityError
from stravalib import Client

from . import strava_api
from application import converters, util
from application.models import db, StravaAccount, Activity
from application.plotlydash.dashboard_activity import calc_power
from application.strava_api.forms import BatchForm
import power.util as putil


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


@strava_api.route('/authorize')
@login_required
def authorize():

  server_url = os.environ.get(
    'DISTILLINGFLASK_SERVER_URL',
    'http://localhost:5000'
  )

  return redirect(Client().authorization_url(
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

  token = Client().exchange_code_for_token(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    code=request.args.get('code'),
  )

  athlete = Client(access_token=token['access_token']).get_athlete()

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
  db.session.commit()

  # Redirect them to the main admin
  return redirect(url_for('route_blueprint.admin_landing'))


@strava_api.route('/activities', methods=['GET', 'POST'])
@login_required
def display_activity_list():
  """Display list of strava activities to view in their own Dashboard."""
  if not current_user.has_authorized:
    return redirect(url_for('strava_api.authorize'))
    # '?after="/strava/activities"'

  print(f'Acct: {current_user.strava_account}')
  print(f'expires_at: {current_user.strava_account.expires_at}')

  token = current_user.strava_account.get_token()
  client = Client(access_token=token['access_token'])

  activities = list(client.get_activities(
    # page=request.args.get('page'),  # stravalib does not accept this param
    limit=request.args.get('limit')  # stravalib does not actually use this param
  ))

  form = BatchForm()
  if form.validate_on_submit():
      # flash('Activities will be added in the background.')
      # take a moment
      
      # Desired: do the following in the background! 
      # And redirect immediately w/ message.

      # Get all activity ids (assumes everything is a valid run rn)
      activity_ids = []
      page = 1
      while True:
        try:
          activities_next = client.get_activities(
            # page=page,
            limit=200
          )
        except Exception:
          print(f'exception on page {page}')
          break
        if len(activities_next) == 0:
          print(f'Reached end of activities.')
          print(f'(Page: {request.args.get("page")}, '
                f'per page: {request.args.get("limit")})')
          break
        activity_ids.extend([
          activity.id for activity in activities_next
        ])
        page += 1
      print(f'Num. of activities retrieved: {len(activity_ids)}')

      # Get data for each activity and create an entry in db.
      activities = []
      for activity_id in activity_ids:
        df = converters.from_strava_streams(client.get_activity_streams(
          activity_id,
          types=['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
             'heartrate', 'cadence', 'watts', 'temp', 'moving',
             'grade_smooth']
        ))
        calc_power(df)

        if 'NGP' in df.columns:
          # Resample the NGP stream at 1 sec intervals
          # TODO: Figure out how/where to make this repeatable.
          # 1sec even samples make the math so much easier.
          interp_fn = interp1d(df['time'], df['NGP'], kind='linear')
          ngp_1sec = interp_fn([i for i in range(df['time'].max())])

          # Apply a 30-sec rolling average.
          window = 30
          ngp_rolling = pd.Series(ngp_1sec).rolling(window).mean()          
          ngp_ms = putil.lactate_norm(ngp_rolling[29:])
          cp_ms = 1609.34 / (6 * 60 + 30)  # 6:30 mile
          intensity_factor = ngp_ms / cp_ms
          total_hours = (df['time'].iloc[-1] - df['time'].iloc[0]) / 3600
          tss = 100.0 * total_hours * intensity_factor ** 2
        else:
          intensity_factor = None
          tss = None

        activity_data = client.get_activity(activity_id).to_dict()

        activities.append(Activity(
          title=activity_data['name'],
          description=activity_data['description'],
          created=datetime.datetime.utcnow(),  
          recorded=dateutil.parser.isoparse(activity_data['start_date']),
          tz_local=activity_data['timezone'],
          moving_time_s=activity_data['moving_time'],
          elapsed_time_s=activity_data['elapsed_time'],
          # Fields below here not required
          strava_id=activity_data['id'],
          distance_m=activity_data['distance'],
          elevation_m=activity_data['total_elevation_gain'],
          intensity_factor=intensity_factor,
          tss=tss,
        ))

      try:
        db.session.add_all(activities)
        db.session.commit()

      except IntegrityError as e:
        print('There was an error saving the activities.')
        print(e)

      return redirect('/')

  return render_template(
    'strava_api/activity_list.html',
    activities=activities,
    # resp_json=activity_json,
    last_page=(len(activities) != request.args.get('limit', 100)),
    form=form
  )


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
  if current_user.has_authorized:
    db.session.delete(current_user.strava_account)
  db.session.commit()

  return redirect(url_for('route_blueprint.admin_landing'))
