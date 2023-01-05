import json
import os
from unittest import skip, skipIf

from selenium.webdriver.common.by import By

from tests import settings
from tests.util import strava_auth_flow
from .base import LoggedInFunctionalTest


@skipIf(
  settings.SKIP_STRAVA_OAUTH,
  'Skipping tests that actually authenticate with Strava'
)
class StravaAuthTest(LoggedInFunctionalTest):

  def test_can_authorize(self):
    # A new user arrives on the app's admin page and clicks a link to
    # view their strava activities.
    self.browser.find_element(By.LINK_TEXT, 'Authorize with Strava').click()
    
    # Since they haven't yet granted permissions to Strava, they are
    # redirected to an authorization screen on strava's website, which
    # they fill out and submit.
    strava_auth_flow(self.browser)

    # Now that my app has access to the user's strava data, they are
    # redirected back to the main admin page, and notice it has more options:

    # They see links inviting them to visit a list of their Strava activities.
    self.check_for_link_text('Strava activities')

    # In the navbar, they see an indication that they have authorized with
    # Strava, as well as some info about that account.
    navbar = self.browser.find_element(By.TAG_NAME, 'nav')
    self.assertIn('Authorized with Strava as', navbar.get_attribute('innerHTML'))

    # ...as well as a link to revoke the app's access to her Strava data,
    # if they choose.
    revoke_btn = self.check_for_link_text('Revoke access')

    # They navigate to the activity list and have a look around.
    # (never mind - done already in test_strava_list)

    # Then they decide to revoke the app's access to their Strava data.
    revoke_btn.click()

    # And the admin page once again indicates they are disconnected
    # from Strava.
    self.check_for_link_text('Authorize with Strava')

  @skip('duh')
  def test_auth_page_redirects(self):
    # The admin user manually navigates to the strava authorization url,
    # but since they are already authorized with strava, they see a message
    # and are redirected back to the admin page.
    pass