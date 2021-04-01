from . import db


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

  filepath_orig = db.Column(
    db.String(200),
    unique=True,
    nullable=True,
  )
  
  filepath_csv = db.Column(
    db.String(200),
    unique=True,
    nullable=True,
  )
  
  # Maybe
  # Doesn't necessarily exist, but must be unique if it does.
  strava_id = db.Column(
    db.Integer,
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