from flask_wtf import FlaskForm
from wtforms import SubmitField


class BatchForm(FlaskForm):
  submit = SubmitField('Save All Strava Activities')
