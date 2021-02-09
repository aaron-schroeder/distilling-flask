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
# URL_PUBLIC = os.environ.get('URL_PUBLIC')


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


@app.route('/activities')
def display_activity_list():
  """Display list of strava activities to view in Dashboard."""
  #activity_json = stravatalk.get_activities_json(session.get('access_token'))
  activity_json = stravatalk.get_activities_json(ACCESS_TOKEN)
  
  # TODO: Formalize this if I want to use it.
  # with open('activity_list.json', 'w') as outfile:
  #   json.dump(activity_json, outfile)

  return render_template('activity_list.html', resp_json=activity_json)
