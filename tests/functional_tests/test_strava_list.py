from selenium.webdriver.common.by import By
from .base import AuthenticatedUserFunctionalTest


class StravaListTest(AuthenticatedUserFunctionalTest):
  def test_list_displays(self):
    # From the admin page, the user clicks a link to see a list of
    # their Strava activities.
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()

    # They see a list of their strava activities.
    header = self.browser.find_element(By.TAG_NAME, 'h2')
    self.assertIn('Strava activities', header.text)

    # ...