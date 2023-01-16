from flask import render_template, request, jsonify
from stravalib.exc import AccessUnauthorized, RateLimitExceeded

from . import main


def mimetype_json_only(request):
  return (
    request.accept_mimetypes.accept_json and
    not request.accept_mimetypes.accept_html
  )


@main.app_errorhandler(403)
def forbidden(e):
  if mimetype_json_only(request):
    response = jsonify({'error': 'forbidden'})
    response.status_code = 403
    return response
  return render_template('403.html'), 403


@main.app_errorhandler(404)
def page_not_found(e):
  if mimetype_json_only(request):
    response = jsonify({'error': 'not found'})
    response.status_code = 404
    return response
  return render_template('404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
  if mimetype_json_only(request):
    response = jsonify({'error': 'internal server error'})
    response.status_code = 500
    return response
  return render_template('500.html'), 500


@main.app_errorhandler(RateLimitExceeded)
def rate_limit_exceeded(e):
  return f'Strava API rate limit exceeded. Limit = {e.limit}, Timeout = {e.timeout}', 429


@main.app_errorhandler(AccessUnauthorized)
def access_unauthorized(e):
  return f'Bad token passed to Strava API. Error message: {e}'