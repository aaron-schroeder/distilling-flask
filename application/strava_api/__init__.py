from flask import Blueprint

strava_api = Blueprint('strava_api', __name__)

from . import views