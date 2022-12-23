from flask_wtf import FlaskForm
from wtforms import SubmitField


class BatchForm(FlaskForm):
  submit = SubmitField('Save all Strava Activities')
