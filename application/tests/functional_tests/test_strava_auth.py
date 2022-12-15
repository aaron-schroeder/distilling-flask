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
    # A new user arrives on the app's main page and clicks a link to
    # view their strava activities.
    self.browser.get(self.server_url)
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()
    
    # Since they haven't yet granted permissions to Strava, they are
    # redirected to an authorization screen on strava's website, which
    # they fill out and submit.
    strava_auth_flow(self.browser)

    # Now that my app has access to the user's strava data, they are
    # redirected to a list of their strava activities.
    header = self.browser.find_element(By.TAG_NAME, 'h2')
    self.assertIn('Strava activities', header.text)


  @skip('Not ready yet')
  def test_revoke(self):
    # The user successfully authorizes the app to access strava

    # After taking a look at the activity list, they decide the app sucks
    # and choose to revoke its access to their strava data.

    self.fail('finish the test')
