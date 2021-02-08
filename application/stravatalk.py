"""Functions for interacting with the Strava API."""
import os
import json

import requests


def get_activities_json(access_token, limit=None):
  """

  TODO:
    * Docstring.

  `stravalib` implementation for reference:
  `acts = client.get_activities(limit=10)`

  """
  # Get the most recent activities for the athlete.
  # curl -X GET `https://www.strava.com/api/v3/athlete/activities`  \
  #              (?before=&after=&page=&per_page=)
  #      -H "Authorization: Bearer [[token]]"
  # before, after, page, per_page
  data = dict(limit=limit) if limit is not None else None
  resp = requests.get('https://www.strava.com/api/v3/athlete/activities',
                      headers={'Authorization': 'Bearer %s' % access_token})

  return resp.json()


def get_activity_json(activity_id, access_token, types=None):
  """

  TODO:
    * Docstring.

  `stravalib` implementation for reference:
  `activity = client.get_activity(activity_id)`
  """

  if types is None:
    types = ['time', 'latlng', 'distance', 'altitude', 'velocity_smooth',
             'heartrate', 'cadence', 'watts', 'temp', 'moving',
             'grade_smooth']
  fields = ','.join(types)

  # curl -X GET  \
  # "https://www.strava.com/api/v3/activities/${id}/streams/${fields}"  \
  #      -H "Authorization: Bearer ${access_token}"
  resp = requests.get(
      'https://www.strava.com/api/v3/activities/%s/streams/%s'
          % (activity_id, fields),
      headers=dict(Authorization='Bearer %s' % access_token)
  )

  # Lemme grab that json for later
  # TODO: Formalize how this aspect of the app works.
  with open('out/strava_latest.json', 'w') as outfile:
    json.dump(resp.json(), outfile)

  return resp.json()
