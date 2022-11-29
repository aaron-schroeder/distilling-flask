import json
import os
from unittest import skip, skipIf

from selenium.webdriver.common.by import By

from application.tests import settings
from application.tests.util import strava_auth_flow
from .base import LiveStravaFunctionalTest


@skipIf(
  settings.SKIP_STRAVA_API,
  'Skipping tests that hit the real strava API server'
)
class StravaAuthTest(LiveStravaFunctionalTest):

  def test_can_authorize(self):
    self.browser.get(self.server_url)
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()
    
    strava_auth_flow(self.browser)

    self.assertIn(
      'Strava activities',
      self.browser.find_element(By.TAG_NAME, 'h2').text
    )

  @skip('Not ready yet')
  def test_logout(self):
    # The user successfully authorizes the app to access strava

    # After taking a look at the activity list, they decide the app sucks
    # and choose to log out.
    self.wait_for_element(By.ID, 'logout-strava').click()

    self.fail('finish the test')
