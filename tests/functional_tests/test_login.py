import time
from urllib.parse import urljoin

from selenium.webdriver.common.by import By

from .base import FunctionalTest


class LoginTest(FunctionalTest):
  def test_can_log_in(self):
    self.navigate_to_admin()

    pw_input = self.wait_for_element(By.ID, 'password')
    pw_input.send_keys(self.dummy_password)

    self.browser.find_element(By.XPATH, '//button[text()="Log in"]').click()

    # The admin user is logged in!
    self.assertIn(
      'settings',
      self.browser.find_element(By.TAG_NAME, 'h1').text.lower()
    )

    # They see links for authenticating a strava account...
    self.check_for_link_text('Strava Account Connections')

    # ...and a file analysis dashboard.
    self.check_for_link_text('Analyze Activity File')

    # The admin dgafs and logs out.
    self.browser.find_element(By.LINK_TEXT, 'Log Out').click()

    # They are logged out and back on the homepage.
    self.assertEqual(
      self.browser.current_url,
      urljoin(self.server_url, '/')
    )

  def test_wrong_password_no_redirect(self):
    self.navigate_to_admin()

    pw_input = self.wait_for_element(By.ID, 'password')

    login_url = self.browser.current_url

    pw_input.send_keys('wrong_password')

    self.browser.find_element(By.XPATH, '//button[text()="Log in"]').click()

    time.sleep(5)

    self.assertEqual(login_url, self.browser.current_url)

  def test_wrong_password_helptext(self):
    # This tests the dashboard itself. Need to get that func set up.
    pass

  def test_three_strikes(self):
    # A user inputs the wrong password 3 times and is unable to
    # try again until an admin resets the app (or something).
    pass