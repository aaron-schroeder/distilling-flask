import time
from unittest import skipIf

from selenium.webdriver.common.by import By

from .base import (
  AuthenticatedUserFunctionalTest as FunctionalTest
  # FunctionalTest
)


@skipIf(
  FunctionalTest.__name__ == 'FunctionalTest',
  'Test will fail with mocked stravatalk until User model implemented'
)
@skipIf(
  # project_settings.LOCKED_OUT_OF_ACCOUNT,
  True,
  'This test would pass were I not locked out of my Strava acct. Skipping.'
)
class ActivityValidationTest(FunctionalTest):

  def test_no_duplicate_strava_activities(self):
    self.browser.get(self.server_url)
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()

    # They are redirected to their list of strava activities.
    # They click the link for the first activity presented.
    section = self.browser.find_element(By.CLASS_NAME, 'content')
    links = section.find_elements(By.TAG_NAME, 'a')
    links[0].click()

    # TODO: Find a way to start off with an activity in the database.
    btn = self.wait_for_element(By.ID, 'save-activity')
    btn.click()

    time.sleep(5)

    # The user has sudden memory loss and clicks `save activity` again
    btn.click()

    time.sleep(5)

    # They receive an alert that this activity already exists in the
    # database.
    result = self.browser.find_element(By.ID, 'save-result').text
    self.assertIn('error', result)

    # But if they try to save a different activity, they have success.
    self.fail('Finish the test!')