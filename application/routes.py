"""Core Flask app routes."""
import os
import json

from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flask import current_app as app
import pandas
import requests

from application import stravatalk


# Store the ngrok url we are forwarding to.
# TODO: Pull this out of the app so I can put it on GH.
URL_PUBLIC = os.environ.get('URL_PUBLIC')


# Store the strava access token set before running the app.
# This does not work for that:
#session['access_token'] = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')


@app.route('/')
def start_dashapp():
  """Route for the landing page of the Flask app.

  TODO:
    * Rename to something appropriate for what it does.
    * Host `display_activity_list` here in lieu of redirecting.
    * Docstring
  """

  #return redirect('/dashapp/test')
  return redirect(url_for('.display_activity_list'))

#def initialize():
#  redirect_uri = os.path.join(URL_PUBLIC, 'authorized')
#  authorize_url = stravatalk.get_authorize_url(redirect_uri)
#
#  return redirect(authorize_url, code=302)


@app.route('/authorized')
def handle_code():
  """
  TODO:
    * Move this out of the Flask app for GH - out of scope for now.
    * Docstring
  """

  # After the user clicks authorization URL, and a 'code' param will be
  # added to the redirect_uri. This function extracts and processes the
  # code from the GET request corresponding to Strava's redirection of
  # our user. Does that make sense??
  
  # Extract the code from Strava's request to my webapp
  code = request.args.get('code')

  # Send that code in a POST request to Strava 
  token_json = stravatalk.get_token_json(code)

  # Now store that short-lived access token somewhere (a database?)
  # You must also store the refresh token to be used later on to obtain 
  # another valid access token in case the current is already expired
  # An access_token is only valid for 6 hours, store expires_at somewhere
  # and check it before making an API call.
 
  # Store the user's tokens in their session data.
  session['access_token'] = token_json['access_token']
  session['refresh_token'] = token_json['refresh_token']
  session['expires_at'] = token_json['expires_at']

  return redirect(url_for('.display_activity_list')) 


@app.route('/activities')
def display_activity_list():
  """Display list of strava activities to view in Dashboard."""
  #activity_json = stravatalk.get_activities_json(session.get('access_token'))
  activity_json = stravatalk.get_activities_json(ACCESS_TOKEN)
  
  # TODO: Formalize this if I want to use it.
  # with open('activity_list.json', 'w') as outfile:
  #   json.dump(activity_json, outfile)

  return render_template('activity_list.html', resp_json=activity_json)


@app.route('/activity-new/<activity_id>')
def display_activity_new(activity_id):
  # NOT USED in current app iteration.

  # stream_list = stravatalk.get_activity_json(activity_id,
  #                                            ACCESS_TOKEN)
                                               #session.get('access_token'))

  # Create the dash app in real time, which will surely break stuff.
  # Update: Yup. I don't have access to the current application.
  #from application.plotlydash.dashboard_activity import create_dashboard
  #current_app = create_dashboard(current_app, stream_list)

  return redirect('/dash-activity/%s' % activity_id)


@app.route('/activity/<activity_id>')
def display_activity(activity_id):
  # NOT USED in current app iteration.

  stream_list = stravatalk.get_activity_json(activity_id,
                                             ACCESS_TOKEN)
                                             #session.get('access_token'))
  # ['type', 'data', 'series_type', 'original_size', 'resolution']
  #print([stream['type'] for stream in stream_list])
  #print(stream_list[0])

  # Temporary code to grab json response for a sample activity
  with open('activity.json', 'w') as outfile:
    json.dump(stream_list, outfile)  

  stream_dict = {stream['type']: stream['data'] for stream in stream_list}

  # Load the response's json data into a pd.Dataframe.
  df = pandas.DataFrame.from_dict(stream_dict) 
  #df.index.name = 'record'

  # Write the dataframe to a csv file, so that the dashboard may
  # access it.
  #df.to_csv('./data/%s.csv' % activity_id)  
  df.to_csv('data/strava_activity.csv')

  #return render_template('activity_detail.html', a=activity)
  return redirect('/dashapp/%s' % activity_id)


def read_dummy_activity():
  with open('activity.json', 'r') as infile:
    stream_list = json.load(infile)

  stream_dict = {stream['type']: stream['data'] for stream in stream_list}

  # Load the response's json data into a pd.Dataframe.
  df = pandas.DataFrame.from_dict(stream_dict)

  pass


@app.route('/webhook', methods=['GET', 'POST'])
def func():
  # NOT USED in current iteration.
  # TODO: Move to a 2.0 file or something. Separate it out.

  # Creates the endpoint for our webhook
  if request.method == 'POST':
    # Now DO SOMETHING with the event!!
    print(request.get_json())

    return 'EVENT_RECEIVED'

  # Adds support for GET requests to our webhook
  elif request.method == 'GET':
    VERIFY_TOKEN = 'STRAVA'
    args = request.args
    mode = args.get('hub.mode')
    token = args.get('hub.verify_token')
    challenge = args.get('hub.challenge')
    # Checks if a token and mode is in the query string of the request
    if (mode is not None and token is not None):
      # Verifies that the mode and token sent are valid
      if mode == 'subscribe' and token == VERIFY_TOKEN:
        # Responds with the challenge token from the request
        print('WEBHOOK_VERIFIED')
        payload = {'hub.challenge': challenge} #,'hub.mode': 'subscribe'}
        return json.dumps(payload, indent=2)
      else:
        # Responds with '403 Forbidden' if verify tokens do not match
        abort(403)
    else:
      print(2)
      abort(404)
  else:
    print(3)
    abort(404)
