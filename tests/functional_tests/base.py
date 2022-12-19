import json
import multiprocessing
import os
import socket
import time
import unittest
from urllib.parse import urljoin

import dash
from flask import url_for
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from application import db, create_app
from tests.util import get_chromedriver, strava_auth_flow


MAX_WAIT = 10


class LiveServerTestCase(unittest.TestCase):
  """
  Largely based on the LiveServerTestCase from the unmaintained package
  `flask_testing`_, which was based on the class from `django`_.
  Rather than use the unmaintained class, I copied most of the code and
  pared it down to the pieces I needed.

  .. _flask-testing: https://github.com/jarus/flask-testing/blob/v0.8.1/flask_testing/utils.py#L426
  .. _django: https://github.com/django/django/blob/stable/4.1.x/django/test/testcases.py#L1777
  """
  LIVE_STRAVA_API = False

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
    # Get the app, making sure that the global callback list doesn't
    # grow each time a LiveServerTestCase is called.
    # This issue arises because I create the app in the main thread 
    # (which populates GLOBAL_CALLBACK_LIST with my app's callbacks),
    # but run the app in another thread (where GLOBAL_CALLBACK_LIST is
    # transferred to an attribute of the app object and emptied.)
    # Since globals are copied from the thread that spawned them,
    # the dash app can't unset the global variable from its thread.
    # See: https://github.com/plotly/dash/issues/1933
    dash_callback_list_pre = dash._callback.GLOBAL_CALLBACK_LIST.copy()
    self.app = self.create_app()
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

  def browser_get_relative(self, path):
    self.browser.get(urljoin(self.server_url, path))

  def _spawn_live_server(self):
    if self.LIVE_STRAVA_API:
      worker = lambda app, port: app.run(port=port, use_reloader=False)
    else:
      def worker(app, port):
        from unittest.mock import patch
        from tests import mock_stravatalk
        with patch('application.stravatalk', mock_stravatalk):
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

    return create_app(test_config={
      'TESTING': True,
      'SQLALCHEMY_DATABASE_URI': 'sqlite:///mydb.sqlite',
      'SECRET_KEY': 'super secret key'
    })

  def setUp(self):
    self.browser = get_chromedriver()

  def tearDown(self):
    self.browser.quit()
    db.drop_all()
    db.session.remove()

  def wait_for_element(self, by, value):
    start_time = time.time()
    while True:
      try:
        return self.browser.find_element(by, value)
      except WebDriverException as e:
        if time.time() - start_time > MAX_WAIT:
          with open('out.html', 'w') as f:
            f.write(self.browser.page_source)
          raise e
        time.sleep(0.5)

  def check_for_link_text(self, link_text):
    link = self.browser.find_element(By.LINK_TEXT, link_text)
    self.assertIsNotNone(link)
    return link


class LiveStravaFunctionalTest(FunctionalTest):
  LIVE_STRAVA_API = True


class LoggedInFunctionalTest(LiveStravaFunctionalTest):
  def setUp(self):
    super().setUp()
    self.browser_get_relative('/login')
    pw_input = self.wait_for_element(By.ID, 'password')
    pw_input.send_keys('password')
    self.browser.find_element(By.XPATH, '//button[text()="Log in"]').click()


class AuthenticatedUserFunctionalTest(LoggedInFunctionalTest):

  def setUp(self):
    super().setUp()
    self.browser_get_relative(url_for('strava_api.authorize'))
    strava_auth_flow(self.browser)
