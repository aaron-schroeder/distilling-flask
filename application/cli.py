import datetime

import click

from application import create_app
from application.models import db, Activity, StravaAccount
from application.util import units


@click.group(
  # cls=FlaskGroup,
  # create_app=create_app,
  # add_default_commands=False,
)
def cli():
  """Management script for the distilling-flask application."""
  pass


@cli.command()
@click.option(
  '--saved_activity_count',
  default=20,
  help='Number of saved activities with which to pre-populate the database.'
)
@click.option(
  '--strava_activity_count',
  default=100,
  help='Number of strava activities in the simulated Strava API.'
)
@click.option(
  '--short_limit',
  default=100,
)
@click.option(
  '--long_limit',
  default=1000,
)
@click.option(
  '--short_usage',
  default=0,
)
@click.option(
  '--long_usage',
  default=0,
)
# @click.option(
#   '--client',
#   default='application.util.mock_stravalib.SimDevClient'
# )
def rundummy(
  saved_activity_count,
  strava_activity_count,
  short_limit,
  long_limit,
  short_usage,
  long_usage
  # client,
):
  """Run the development server with a mocked strava API."""
  print('mocking stravalib')

  app = create_app(config_name='dummy')

  # app.config['STRAVALIB_CLIENT'] = client
  app.config['MOCK_STRAVALIB_ACTIVITY_COUNT'] = strava_activity_count
  app.config['MOCK_STRAVALIB_SHORT_LIMIT'] = short_limit
  app.config['MOCK_STRAVALIB_LONG_LIMIT'] = long_limit
  app.config['MOCK_STRAVALIB_SHORT_USAGE'] = short_usage
  app.config['MOCK_STRAVALIB_LONG_USAGE'] = long_usage
  
  with app.app_context():
    db.drop_all()
    from flask_migrate import stamp as _stamp
    _stamp(revision='base')

    from flask_migrate import upgrade as _upgrade
    _upgrade()
    
    # Spoof a StravaAccount that has authorized with strava.
    # This will only be used with mockstravalib, not the real thing.
    db.session.add(
      StravaAccount(
        strava_id=123,
        access_token='some_access_token',
        refresh_token='some_refresh_token',
        expires_at=0,
      )
    )
    db.session.commit()

    # optionally pre-populate the DB with dummy activities
    if saved_activity_count:
      db.session.add_all(
        Activity(
          id=i,
          title=f'Activity {i}',
          description='',
          created=datetime.datetime.now(),
          recorded=datetime.datetime.now() - datetime.timedelta(days=i),
          tz_local='UTC',
          strava_id=i,
          strava_acct_id=123,
          distance_m=10000,
          elevation_m=500,
          elapsed_time_s=3600,
          moving_time_s=3600,
          ngp_ms=units.pace_to_speed('8:30')
        )
        for i in range(saved_activity_count)
      )
      db.session.commit()

  app.run()


@cli.command()
def rundev():
  app = create_app(config_name='dev')
  app.run()