import os

from flask_login import UserMixin

from application import db, login
from application import stravatalk


CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


class Activity(db.Model):
  """Data model for activities."""

  # Only need to define this if I want to override default lowercase
  # eg __tablename__ = 'activity' by default
  # __tablename__ = 'activities'

  id = db.Column(
    db.Integer,
    primary_key=True
  )

  title = db.Column(
    db.String(100),
    unique=False,
    nullable=True,  # Why force it?
  )

  description = db.Column(
    db.Text,
    unique=False,
    nullable=True,
  )

  created = db.Column(
    db.DateTime,
    unique=False,
    nullable=False
  )

  recorded = db.Column(
    db.DateTime,
    unique=False,
    nullable=False
  )

  tz_local = db.Column(
    db.String(40),  # I checked and 32 is max length
    unique=False,
    nullable=False,
    default='UTC',
  )
  
  # Doesn't necessarily exist, but must be unique if it does.
  strava_id = db.Column(
    db.BigInteger,
    unique=True,
    nullable=True,
  )

  # Maybe (strava, file upload, etc)
  # String
  # data_source = ...

  # Nullable because not every activity has latlons, so getting vals 
  # might not be possible.
  distance_m = db.Column(
    db.Float,
    unique=False,
    nullable=True,
  )

  # Figured rounding to the nearest meter isn't a loss of precision.
  # Nullable because not every activity has latlons, so getting vals 
  # might not be possible.
  elevation_m = db.Column(
    db.Integer,
    unique=False,
    nullable=True,
  )

  # I think this should be required. All activities should have time as
  # a bare minimum.
  elapsed_time_s = db.Column(
    db.Integer,
    unique=False,
    nullable=False,
  )

  # I think this should be required. Can be the same as elapsed_time_s
  # in a pinch.
  moving_time_s = db.Column(
    db.Integer,
    unique=False,
    nullable=False,
  )

  # Might make this required - I'd like every activity to have a
  # quantification of stress. This + duration = stress. Still thinking
  # it through, though.
  #
  # Also, consider that there might be multiple intensity factors
  # corresponding to different data streams or methods of calculation.
  intensity_factor = db.Column(
    db.Float,
    unique=False,
    nullable=True,
  )

  # Maybe (could be duplicate info w/ IF)
  tss = db.Column(
    db.Float,
    unique=False,
    nullable=True,
  )

  def __repr__(self):
      return '<Activity {}>'.format(self.id)


class AdminUser(UserMixin):
  id = 1
  # strava_accounts = db.relationship(
  #   'StravaAccount',
  #   backref='admin_user',
  #   lazy=True
  # )

  def check_password(self, password):
    # password_correct = config.get('settings', 'password')
    password_correct = os.environ.get('PASSWORD', None)
    if password_correct:
      return password == password_correct

  @property
  def strava_account(self):
    accounts = StravaAccount.query.all()
    if len(accounts) == 0:
      return None
    return accounts[0]

  @property
  def has_authorized(self):
    return self.strava_account is not None

  def __repr__(self):
    return '<Admin User>'


@login.user_loader
def load_user(id):
  return AdminUser()


class StravaAccount(db.Model):
  # admin_user_id = db.Column(
  #   db.Integer,
  #   db.ForeignKey('admin_user.id'),
  #   nullable=False
  # )
  # admin_user_id = 1
  strava_id = db.Column(
    db.Integer,
    primary_key=True
  )
  access_token = db.Column(db.String())
  refresh_token = db.Column(db.String())
  expires_at = db.Column(db.Integer)
  # email = db.Column(db.String)

  def get_token(self):

    # reconstruct the required elements of strava's access token
    token = dict(
      access_token=self.access_token,
      refresh_token=self.refresh_token,
      expires_at=self.expires_at,
    )

    # refresh if necessary
    return stravatalk.refresh_token(token, CLIENT_ID, CLIENT_SECRET)

  @property
  def url(self):
    return f'https://www.strava.com/athletes/{self.strava_id}'