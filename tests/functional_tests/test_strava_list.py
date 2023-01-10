from selenium.webdriver.common.by import By
from .base import AuthenticatedUserFunctionalTest


class StravaListTest(AuthenticatedUserFunctionalTest):
  def test_list_displays(self):
    # From the acct page, the user clicks a link to see a list of
    # their Strava activities.
    self.wait_for_element(By.PARTIAL_LINK_TEXT, 'Activities').click()

    # They see a list of their strava activities.
    header = self.wait_for_element(By.TAG_NAME, 'h2')
    self.assertIn('strava activities', header.text.lower())

    # ...
  
  def test_list_redirects(self):
    # They go to the activity list but since they haven't yet granted 
    # permissions to Strava, they are
    # redirected to an authorization screen on strava's website, which
    # they fill out and submit.
    pass