import time
from unittest import skip, skipIf
from urllib.parse import urlparse

from selenium.webdriver.common.by import By

from tests import settings
from .base import AuthenticatedUserFunctionalTest


@skipIf(
  settings.SKIP_STRAVA_OAUTH,
  'This test would pass were I not locked out of my Strava acct. Skipping.'
)
@skip('This is a huge operation depending on the linked strava acct.')
class TestBatchSave(AuthenticatedUserFunctionalTest):
  def test_can_save_activity(self):
    # An authenticated user visits the strava activity list.
    self.check_for_link_text('Strava activities').click()

    # They notice a new button to save all the activities associated
    # with their Strava account. 
    save_all_input = self.wait_for_element(By.ID, 'submit')

    # Since they have no saved activities, they click it to save some time.
    time_init = time.time()
    save_all_input.click()

    # They are immediately redirected to the training log dashboard and 
    # a message appears telling them that the activities are being added
    # in the background.
    self.assertLessEqual(time.time()-time_init, 1.0)
    self.assertEqual(
      urlparse(self.browser.current_url).path,
      '/'
    )

    self.fail('finish the test')
