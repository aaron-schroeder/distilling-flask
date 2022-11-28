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
class TestStravaSave(FunctionalTest):
  def test_can_save_activity(self):
    # From the landing page, the user navigates to their list of
    # Strava activities.
    self.browser.get(self.server_url)
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()

    # They are redirected to their list of strava activities.
    # They click the link for the first activity presented.
    section = self.wait_for_element(By.CLASS_NAME, 'content')
    links = section.find_elements(By.TAG_NAME, 'a')
    links[0].click()

    # They wait a million years for the appearance of a button that
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
    self.fail('Finish the test!')

    # self.client.post('/', data={'item_text': 'A new list item'})
    # self.assertEqual(Item.objects.count(), 1)
    # new_item = Item.objects.first()
    # self.assertEqual(new_item.text, 'A new list item')

    # They check out the activity log to see if it updated.

    # They find the saved activity in the calendar view,
    # with summary stats and a link back to the saved activity view.