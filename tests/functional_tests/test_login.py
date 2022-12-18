from selenium.webdriver.common.by import By

from .base import FunctionalTest


class LoginTest(FunctionalTest):
  def test_can_log_in(self):
    self.browser.get(self.server_url)

    self.browser.find_element(By.ID, 'login').click()

    pw_input = self.wait_for_element(By.ID, 'password')
    pw_input.send_keys('password')

    # She is logged in! 
    # She sees links for authenticating a strava account...
    # TODO

    # ...and a file analysis dashboard.
    self.check_for_link_text('Analyze an activity file (.gpx, .fit, .tcx, .csv)')

    # She dgafs and logs out.
    self.browser.find_element(By.LINK_TEXT, 'Log out').click()

    # She is logged out!

  def test_wrong_password_helptext(self):
    pass