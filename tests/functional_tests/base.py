import json
import multiprocessing
import os
import socket
import time
import unittest
from unittest.mock import patch
from urllib.parse import urljoin

import dash
from flask import url_for
from selenium.common.exceptions import (
  ElementClickInterceptedException,
  WebDriverException
)
from selenium.webdriver.common.by import By

from application import create_app
from application.models import db, StravaAccount
from tests.util import get_chromedriver, strava_auth_flow, wait_for_element
from tests import mock_stravalib, settings


MAX_WAIT = 20


class LiveServerTestCase(unittest.TestCase):
  """
  Largely based on the LiveServerTestCase from the unmaintained package
  `flask_testing`_, which was based on the class from `django`_.
  Rather than use the unmaintained class, I copied most of the code and
  pared it down to the pieces I needed.

  .. _flask-testing: https://github.com/jarus/flask-testing/blob/v0.8.1/flask_testing/utils.py#L426
  .. _django: https://github.com/django/django/blob/stable/4.1.x/django/test/testcases.py#L1777
  """
  def create_app(self):
    """
    Create your Flask app here, with any
    configuration you need.
    """
    raise NotImplementedError

  def __call__(self, result=None):
    """
    Does the required setup, doing it here means you don't have to
    call super.setUp in subclasses.
    """
    dash_callback_list_pre = dash._callback.GLOBAL_CALLBACK_LIST.copy()

    self.app = self.create_app()
    self.app.config['STRAVA_API_BACKEND'] = (
      'tests.mock_stravalib.Client' if settings.SKIP_STRAVA_API 
      else 'stravalib.Client'
    )
    
    # Make sure that the global callback list doesn't
    # grow each time a LiveServerTestCase is called.
    # This issue arises because I create the app in the main thread 
    # (which populates GLOBAL_CALLBACK_LIST with my app's callbacks),
    # but run the app in another thread (where GLOBAL_CALLBACK_LIST is
    # transferred to an attribute of the app object and emptied.)
    # Since globals are copied from the thread that spawned them,
    # the dash app can't unset the global variable from its thread.
    # See: https://github.com/plotly/dash/issues/1933
    if (
      len(dash_callback_list_pre) > 0 
      and len(dash._callback.GLOBAL_CALLBACK_LIST) > len(dash_callback_list_pre)
    ):
      dash._callback.GLOBAL_CALLBACK_LIST = dash_callback_list_pre

    # self._configured_port = self.app.config.get('LIVESERVER_PORT', 5000)
    self._configured_port = 5000

    # We need to create a context in order for extensions to catch up
    self._ctx = self.app.test_request_context()
    self._ctx.push()

    db.create_all()

    if settings.SKIP_STRAVA_API:
      # Spoof a StravaAccount that has authorized with strava.
      # This will only be used with mockstravatalk, not the real thing.
      db.session.add(
        StravaAccount(
          strava_id=123,
          access_token='some_access_token',
          refresh_token='some_refresh_token',
          expires_at=0,
        )
      )
      db.session.commit()

    try:
      self._spawn_live_server()
      super(LiveServerTestCase, self).__call__(result)
    finally:
      self._post_teardown()
      self._terminate_live_server()

  @property
  def server_url(self):
    """
    Return the url of the test server
    """
    return f'http://localhost:{self._configured_port}'

  def _spawn_live_server(self):
    if not settings.SKIP_STRAVA_API:
      worker = lambda app, port: app.run(port=port, use_reloader=False)
    else:
      def worker(app, port):
        with patch('stravalib.Client', mock_stravalib.Client):
          app.run(port=port, use_reloader=False)
    
    self._process = multiprocessing.Process(
        target=worker,
        args=(self.app, self._configured_port)
    )

    self._process.start()

    # We must wait for the server to start listening, but give up
    # after a specified maximum timeout
    timeout = int(self.app.config.get('LIVESERVER_TIMEOUT', 5))
    start_time = time.time()

    while True:
      elapsed_time = (time.time() - start_time)
      if elapsed_time > timeout:
        raise RuntimeError(
          f'Failed to start the server after {timeout:d} seconds. '
        )
      if self._can_ping_server():
        break

  def _can_ping_server(self):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      sock.connect(('localhost', self._configured_port))
    except socket.error as e:
      success = False
    else:
      success = True
    finally:
      sock.close()

    return success

  def _post_teardown(self):
    if getattr(self, '_ctx', None) is not None:
      self._ctx.pop()
      del self._ctx

  def _terminate_live_server(self):
    if self._process:
      self._process.terminate()


class FunctionalTest(LiveServerTestCase):
  dummy_password = 'ilovestrava'

  def create_app(self):
    with open('client_secrets.json', 'r') as f:
      client_secrets = json.load(f)
    os.environ['STRAVA_CLIENT_ID'] = client_secrets['installed']['client_id']
    os.environ['STRAVA_CLIENT_SECRET'] = client_secrets['installed']['client_secret']
    os.environ['PASSWORD'] = self.dummy_password

    return create_app(config_name='test')

  def setUp(self):
    self.browser = get_chromedriver()

  def tearDown(self):
    self.browser.quit()
    db.drop_all()
    db.session.remove()

  def wait_for_element(self, by, value):
    return wait_for_element(self.browser, by, value)

  def check_for_link_text(self, link_text):
    link = self.browser.find_element(By.LINK_TEXT, link_text)
    self.assertIsNotNone(link)
    return link

  def browser_get_relative(self, path):
    self.browser.get(urljoin(self.server_url, path))

  def navigate_to_admin(self):
    self.browser_get_relative('/')
    try:
      self.wait_for_element(
        By.XPATH, 
        '//button[contains(@class, "toggler")]'
      ).click()
    except ElementClickInterceptedException:
      print(self.browser.page_source)
    self.wait_for_element(By.LINK_TEXT, 'Admin').click()


class LoggedInFunctionalTest(FunctionalTest):
  def setUp(self):
    super().setUp()
    self.browser_get_relative('/login')
    pw_input = self.wait_for_element(By.ID, 'password')
    pw_input.send_keys(self.dummy_password)
    self.browser.find_element(By.XPATH, '//button[text()="Log in"]').click()


class AuthenticatedUserFunctionalTest(LoggedInFunctionalTest):

  def setUp(self):
    super().setUp()
    if settings.SKIP_STRAVA_API:
      # No need to go through real auth process, since the
      # database is pre-spoofed.
      time.sleep(0.2)
      self.browser_get_relative(url_for('strava_api.manage'))
      time.sleep(0.2)
    else:
      time.sleep(0.2)
      self.browser_get_relative(url_for('strava_api.authorize'))
      time.sleep(0.2)
      strava_auth_flow(self.browser)
