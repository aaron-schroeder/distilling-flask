"""
Refs:
  https://www.obeythetestinggoat.com/book/chapter_01.html
  https://stackoverflow.com/questions/64717302/deprecationwarning-executable-path-has-been-deprecated-selenium-python
  https://www.obeythetestinggoat.com/book/chapter_02_unittest.html
"""
import json
import multiprocessing
import os
import socket
import socketserver
import time
import unittest
from urllib.parse import urlparse, urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from application import db, create_app, stravatalk


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

    # Get the app
    self.app = self.create_app()

    self._configured_port = self.app.config.get('LIVESERVER_PORT', 5000)
    self._port_value = multiprocessing.Value('i', self._configured_port)

    # We need to create a context in order for extensions to catch up
    self._ctx = self.app.test_request_context()
    self._ctx.push()

    try:
      self._spawn_live_server()
      super(LiveServerTestCase, self).__call__(result)
    finally:
      self._post_teardown()
      self._terminate_live_server()

  def get_server_url(self):
    """
    Return the url of the test server
    """
    return 'http://localhost:%s' % self._port_value.value

  def _spawn_live_server(self):
    self._process = None
    port_value = self._port_value

    def worker(app, port):
      # Based on solution: http://stackoverflow.com/a/27598916
      # Monkey-patch the server_bind so we can determine the port bound by Flask.
      # This handles the case where the port specified is `0`, which means that
      # the OS chooses the port. This is the only known way (currently) of getting
      # the port out of Flask once we call `run`.
      original_socket_bind = socketserver.TCPServer.server_bind
      def socket_bind_wrapper(self):
        ret = original_socket_bind(self)

        # Get the port and save it into the port_value, so the parent process
        # can read it.
        (_, port) = self.socket.getsockname()
        port_value.value = port
        socketserver.TCPServer.server_bind = original_socket_bind
        return ret

      socketserver.TCPServer.server_bind = socket_bind_wrapper
      app.run(port=port, use_reloader=False)

    self._process = multiprocessing.Process(
        target=worker, args=(self.app, self._configured_port)
    )

    self._process.start()

    # We must wait for the server to start listening, but give up
    # after a specified maximum timeout
    timeout = self.app.config.get('LIVESERVER_TIMEOUT', 5)
    start_time = time.time()

    while True:
      elapsed_time = (time.time() - start_time)
      if elapsed_time > timeout:
        raise RuntimeError(
          'Failed to start the server after %d seconds. ' % timeout
        )

      if self._can_ping_server():
        break

  def _can_ping_server(self):
    host, port = self._get_server_address()
    if port == 0:
      # Port specified by the user was 0, and the OS has not yet assigned
      # the proper port.
      return False

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      sock.connect((host, port))
    except socket.error as e:
      success = False
    else:
      success = True
    finally:
      sock.close()

    return success

  def _get_server_address(self):
    """
    Gets the server address used to test the connection with a socket.
    Respects both the LIVESERVER_PORT config value and overriding
    get_server_url()
    """
    parts = urlparse(self.get_server_url())

    host = parts.hostname
    port = parts.port

    if port is None:
      if parts.scheme == 'http':
        port = 80
      elif parts.scheme == 'https':
        port = 443
      else:
        raise RuntimeError(
          'Unsupported server url scheme: %s' % parts.scheme
        )

    return host, port

  def _post_teardown(self):
    if getattr(self, '_ctx', None) is not None:
      self._ctx.pop()
      del self._ctx

  def _terminate_live_server(self):
    if self._process:
      self._process.terminate()


class NewVisitorTest(LiveServerTestCase):
  def create_app(self):

    with open('client_secrets.json', 'r') as f:
      client_secrets = json.load(f)
    client_id = client_secrets['installed']['client_id']
    client_secret = client_secrets['installed']['client_secret']

    access_token = stravatalk.refresh_access_token('tokens.json', client_id, client_secret)

    os.environ['ACCESS_TOKEN'] = access_token

    return create_app(test_config={
      'TESTING': True,
      'SQLALCHEMY_DATABASE_URI': os.environ.get(
        'TEST_DATABASE_URL',
        'sqlite://'  # in-memory db
      )
    })

  def setUp(self):
    # Opt 1: Set up and use Firefox webdriver, like in Chapter 1.
    # browser = webdriver.Firefox()

    # Option 2: Use existing Chrome driver setup
    # WSL (Linux) setup
    s = Service(ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    # Note: the following 3 options are necessary to run in WSL.
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    self.browser = webdriver.Chrome(
      service=s,
      options=chrome_options
    )

  def tearDown(self):
    self.browser.quit()
    db.drop_all()
    db.session.remove()

  def check_for_link_text(self, link_text):
    self.assertIsNotNone(
      self.browser.find_element(By.LINK_TEXT, link_text))

  def test_can_see_landing_page(self):

    # Edith has heard about a cool new online to-do app. She goes
    # to check out its homepage.
    self.browser.get(self.get_server_url())

    # She notices the page title and header welcomes her to
    # the app and tells her its name.
    self.assertIn('Welcome - Training Zealot', self.browser.title)
    header_text = self.browser.find_element(By.TAG_NAME, 'h2').text
    self.assertIn('Welcome', header_text)
    
    # She sees a navigation bar that takes her back to the app's home page.
    navbar = self.browser.find_element(
      By.XPATH,
      '//nav[contains(@class, "navbar")]/a[contains(@class, "navbar-brand")]'
    )
    self.assertIn('The Training Zealot Analysis Platform', navbar.text)
    self.assertEqual(
      navbar.get_attribute('href'),
      urljoin(self.get_server_url(), '/')
    )

    # She sees links inviting her to visit a list of her Strava activities...
    self.check_for_link_text('Strava activities')

    # ...a training log dashboard...
    self.check_for_link_text('Training log dashboard')

    # ...and a file analysis dashboard.
    self.check_for_link_text('Analyze an activity file (.gpx, .fit, .tcx, .csv)')

    self.fail('Finish the test!')

    # She clicks a link to visit the page for activity file analysis.
    
    # There is a widget to upload her activity file

    # Satisfied, she goes back to sleep

  def test_can_save_activity(self):
    # From the landing page, the user navigates to their list of
    # Strava activities.
    self.browser.get(self.get_server_url())
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()

    # TODO: A detour: they must approve the app's use of their strava data.
    # They do.

    # They are redirected to their list of strava activities.
    # They click the link for the first activity presented.
    section = self.browser.find_element(By.CLASS_NAME, 'content')
    links = section.find_elements(By.TAG_NAME, 'a')
    print(links[0].text)
    links[0].click()

    # Wait a million years for the dashboard to load
    # and populate with data.
    time.sleep(90)

    # On the activity dashboard, there is an option to save the
    # Strava activity into the database. The user clicks this
    # without editing any of the inputs on the page.
    btn = self.browser.find_element(By.ID, 'save-activity')
    self.assertEqual(btn.text, 'Save activity to DB')
    btn.click()

    time.sleep(5)

    # The activity is saved successfully, and the user sees a message
    # indicating success.
    result = self.browser.find_element(By.ID, 'save-result').text
    self.assertIn('Activity saved successfully!', result)

    # The activity is saved successfully, and they are redirected to
    # its "Saved Activity" page.
    self.fail('Finish the test!')

    # self.client.post('/', data={'item_text': 'A new list item'})
    # self.assertEqual(Item.objects.count(), 1)
    # new_item = Item.objects.first()
    # self.assertEqual(new_item.text, 'A new list item')

    # They check out the activity log to see if it updated.

    # They find the saved activity in the calendar view,
    # with summary stats and a link back to the saved activity view.

    # The user has sudden memory loss and goes back to the strava activity page

    # They click `save activity` again

    # They receive an alert that this activity already exists in their
    # database.
