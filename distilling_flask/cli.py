import datetime
import os
import shutil

import click
from flask import current_app
from flask.cli import FlaskGroup, with_appcontext

import distilling_flask as distilling_flask
from distilling_flask import create_app
from distilling_flask.models import db, Activity, StravaAccount
from distilling_flask.util import units


_MIGRATION_DIR = os.path.join(distilling_flask.__path__[0], 'migrations')


class CommandError(Exception):
  """Verbatim from Django.

  Exception class indicating a problem while executing a management
  command.

  If this exception is raised during the execution of a management
  command, it will be caught and turned into a nicely-printed error
  message to the appropriate output stream (i.e., stderr); as a
  result, raising this exception (with a sensible description of the
  error) is the preferred way to indicate that something has gone
  wrong in the execution of a command.

  Ref:
    https://github.com/django/django/blob/8a844e761d098d4005725f991a5e120a1f17cb70/django/core/management/base.py#L21
  """

  def __init__(self, *args, returncode=1, **kwargs):
    self.returncode = returncode
    super().__init__(*args, **kwargs)


@click.group(
  cls=FlaskGroup,
  create_app=create_app,
  # add_default_commands=False,
)
def context_cli():
  pass

@context_cli.command()
@with_appcontext
def start():
  # _setup_env()

  # _apply_database_migrations()
  # AKA:
  # connection_created.connect(_set_sqlite_fix_pragma)
  # if not is_database_synchronized(DEFAULT_DB_ALIAS):
  from flask_migrate import upgrade as _upgrade
  print('Initializing database..')
  _upgrade(directory=_MIGRATION_DIR)



@click.group()
def cli():
  """Management script for the distilling-flask distilling_flask."""
  pass


@cli.command()
@click.argument('app_name')
def init(app_name):
  """Creates a distilling-flask project directory structure
  for the given project name in the current directory.
  """
  top_dir = os.path.join(os.getcwd(), app_name)
  try:
    os.makedirs(top_dir)
  except FileExistsError:
    raise CommandError(f'{top_dir} already exists')
  except OSError as e:
    raise CommandError(e)
  
  base_name = 'app_name'

  template_dir = os.path.join(distilling_flask.__path__[0], 'conf', 'app_template')
  prefix_length = len(template_dir) + 1

  for root, dirs, files in os.walk(template_dir):
    path_rest = root[prefix_length:]
    relative_dir = path_rest.replace(base_name, app_name)
    if relative_dir:
      target_dir = os.path.join(top_dir, relative_dir)
      os.makedirs(target_dir, exist_ok=True)

    for dirname in dirs[:]:
      if dirname.startswith(".") or dirname == "__pycache__":
        dirs.remove(dirname)

    for filename in files:
      if filename.endswith((".pyo", ".pyc", ".py.class")):
        # Ignore some files as they cause various breakages.
        continue
      old_path = os.path.join(root, filename)
      new_path = os.path.join(
        top_dir, relative_dir, filename.replace(base_name, app_name)
      )

      for old_suffix, new_suffix in (".py-tpl", ".py"),:
          if new_path.endswith(old_suffix):
            new_path = new_path[:-len(old_suffix)] + new_suffix
            break  # Only rewrite once

      if os.path.exists(new_path):
        raise CommandError(
          f'{new_path} already exists. Overlaying a project into an existing '
          'directory won\'t replace conflicting files.'
        )
      
      # # Only render the Python files, as we don't want to
      # # accidentally render Django templates files
      # if new_path.endswith(extensions) or filename in extra_files:
      #   with open(old_path, encoding="utf-8") as template_file:
      #     content = template_file.read()
      #   template = Engine().from_string(content)
      #   content = template.render(context)
      #   with open(new_path, "w", encoding="utf-8") as new_file:
      #     new_file.write(content)
      # else:
      shutil.copyfile(old_path, new_path)

      # if self.verbosity >= 2:
      # self.stdout.write("Creating %s" % new_path)

      # self.apply_umask(old_path, new_path)
      # self.make_writeable(new_path)

@context_cli.command()
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
#   default='distilling_flask.util.mock_stravalib.SimDevClient'
# )
@with_appcontext
def seed(
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

  # TODO: Figure out where this gets implemented.
  # app.config['STRAVALIB_CLIENT'] = client
  # current_app.config['MOCK_STRAVALIB_ACTIVITY_COUNT'] = strava_activity_count
  # current_app.config['MOCK_STRAVALIB_SHORT_LIMIT'] = short_limit
  # current_app.config['MOCK_STRAVALIB_LONG_LIMIT'] = long_limit
  # current_app.config['MOCK_STRAVALIB_SHORT_USAGE'] = short_usage
  # current_app.config['MOCK_STRAVALIB_LONG_USAGE'] = long_usage
  
  db.drop_all()
  from flask_migrate import stamp as _stamp
  _stamp(directory=_MIGRATION_DIR, revision='base')

  from flask_migrate import upgrade as _upgrade
  _upgrade(directory=_MIGRATION_DIR)
  
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


@cli.command()
def rundev():
  app = create_app(config_name='dev')
  app.run()