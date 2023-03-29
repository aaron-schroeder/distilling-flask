import datetime
from importlib import import_module
import os
import sys

from flask import current_app
import pandas as pd
import sqlalchemy as sa

from distilling_flask import db
# from distilling_flask.io_storages.strava.models import StravaImportStorage
from distilling_flask.util import power, units


class AdminUser:
  id = 1

  def check_password(self, password):
    # password_correct = config.get('settings', 'password')
    password_correct = os.environ.get('PASSWORD', None)
    if password_correct:
      return password == password_correct

  # strava_accounts = db.relationship(
  #   'StravaImportStorage',
  #   backref='admin_user',
  #   lazy=True
  # )

  @property
  def strava_accounts(self):
    # return StravaImportStorage.query.all()
    return []  # HACK

  @property
  def settings(self):
    return UserSettings.query.get(self.id)

  def __repr__(self):
    return '<Admin User>'


def cached_import(module_path, class_name):
  """
  based on `django.utils.module_loading.import_string`
  """

  # Check whether module is loaded and fully initialized.
  if not (
    (module := sys.modules.get(module_path))
    and (spec := getattr(module, "__spec__", None))
    and getattr(spec, "_initializing", False) is False
  ):
    module = import_module(module_path)
  return getattr(module, class_name)


def import_string(dotted_path):
  """
  Import a dotted module path and return the attribute/class designated by the
  last name in the path. Raise ImportError if the import failed.

  based on `django.utils.module_loading.import_string`
  """
  try:
    module_path, class_name = dotted_path.rsplit(".", 1)
  except ValueError as err:
    raise ImportError("%s doesn't look like a module path" % dotted_path) from err

  try:
    return cached_import(module_path, class_name)
  except AttributeError as err:
    raise ImportError(
      'Module "%s" does not define a "%s" attribute/class'
      % (module_path, class_name)
    ) from err


class UserSettings(db.Model):
  id = db.Column(
    db.Integer,
    primary_key=True
  )

  cp_ms = db.Column(
    db.Float,
    nullable=False,
    server_default=sa.text(str(units.pace_to_speed('6:30')))
  )

  @property
  def ftp_ms(self):
    return self.cp_ms
  