import json
import os
from unittest import skip, skipIf

from selenium.webdriver.common.by import By

from tests import settings
from tests.util import strava_auth_flow
from .base import LoggedInFunctionalTest


@skipIf(
  settings.SKIP_STRAVA_API,
  'Skipping tests that hit the real strava API server'
)
class StravaAuthTest(LoggedInFunctionalTest):

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
    # redirected back to the main admin page, and notice it has more options.

    # They see links inviting them to visit a list of their Strava activities...
    self.check_for_link_text('Strava activities')

    # ...a training log dashboard... 
    # NOTE: This should only appear after an activity is saved.
    #       Or it shouldn't freak out if there are no saved activities.
    self.check_for_link_text('Training log dashboard')

    # ...and to revoke the app's access to her Strava data, if they choose.
    # TODO
  
  @skip('Not ready yet')
  def test_revoke(self):
    # The user successfully authorizes the app to access strava

    # After taking a look at the activity list, they decide the app sucks
    # and choose to revoke its access to their strava data.

    self.fail('finish the test')
