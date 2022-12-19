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
  
  def test_list_redirects(self):
    # They go to the activity list but since they haven't yet granted 
    # permissions to Strava, they are
    # redirected to an authorization screen on strava's website, which
    # they fill out and submit.
    pass