import time
from unittest import skipIf

from selenium.webdriver.common.by import By

from tests import settings
from .base import AuthenticatedUserFunctionalTest


@skipIf(
  settings.SKIP_STRAVA_OAUTH,
  'This test would pass were I not locked out of my Strava acct. Skipping.'
)
class TestStravaSave(AuthenticatedUserFunctionalTest):
  def test_can_save_activity(self):
    # The user checks the training log view and sees there are no
    # activities to display.
    self.browser_get_relative('/')
    content_container = self.wait_for_element(
      By.XPATH,
      '//*[@id="_pages_content"]//div[contains(@class, "container")]'
    )
    self.assertIn(
      'No activities have been saved yet.',
      content_container.get_attribute('innerHTML')
    )

    # The user navigates to their list of Strava activities.
    self.navigate_to_admin()
    self.browser.find_element(By.LINK_TEXT, 'Manage Strava Connections').click()
    self.assertEqual(
      self.browser.find_element(By.TAG_NAME, 'h2').text,
      'Manage Connected Strava Accounts'
    )
    self.wait_for_element(By.PARTIAL_LINK_TEXT, 'Activities').click()

    # They are redirected to their list of strava activities.
    # They click the link for the first activity presented.
    section = self.wait_for_element(By.CLASS_NAME, 'content')
    links = section.find_elements(By.TAG_NAME, 'a')
    links[0].click()

    # They wait for the appearance of a button that
    # allows them to save the activity to the database.
    btn = self.wait_for_element(By.ID, 'save-activity')
    self.assertIn('Save activity', btn.text)

    # Without editing any of the inputs on the page, they click it.
    btn.click()

    time.sleep(5)

    # Current (passing) path:
    # The activity is saved successfully, and the user sees a message
    # indicating success.
    result = self.browser.find_element(By.ID, 'save-result').text
    self.assertIn('Activity saved successfully!', result)

    # Desired path:
    # The activity is saved successfully, and they are redirected to
    # its "Saved Activity" page.
    self.assertIn(
      '/saved/',
      self.browser.current_url
    )

    # They check out the activity log to see if it updated.
    self.browser_get_relative('/')

    # They find the saved activity in the calendar view,
    # with summary stats and a link back to the saved activity view.
    self.assertNotIn(
      'No activities have been saved yet.',
      self.browser.page_source
    )
