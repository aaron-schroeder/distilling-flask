import time
from unittest import skip

from selenium.webdriver.common.by import By

from .base import AuthenticatedUserFunctionalTest


@skip('This test would pass were I not locked out of my Strava acct. Skipping.')
class ActivityValidationTest(AuthenticatedUserFunctionalTest):

  def test_no_duplicate_strava_activities(self):
    # TODO: Find a way to start off with an activity in the database.

    # The user navigates to their list of Strava activities.
    self.wait_for_element(By.PARTIAL_LINK_TEXT, 'Activities').click()

    # They are redirected to their list of strava activities.
    # They click the link for the first activity presented.
    datatable = self.wait_for_element(By.ID, 'datatable-activity')
    datatable.find_elements(
      By.XPATH, 
      '//td[@data-dash-column="Title"]//a'
    )[0].click()

    btn = self.wait_for_element(By.ID, 'save-activity')
    activity_url = self.browser.current_url
    btn.click()

    time.sleep(5)

    # The user has sudden memory loss and tries to save the activity again.
    self.browser.get(activity_url)
    btn = self.wait_for_element(By.ID, 'save-activity')
    btn.click()

    time.sleep(5)

    # They receive an alert that this activity already exists in the
    # database.
    result = self.browser.find_element(By.ID, 'save-result').text
    self.assertIn('error', result)

    # But if they try to save a different activity, they have success.
    self.fail('Finish the test!')