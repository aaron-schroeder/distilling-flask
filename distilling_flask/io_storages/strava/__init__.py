from flask import Blueprint


strava = Blueprint('strava_api', __name__)


from . import views