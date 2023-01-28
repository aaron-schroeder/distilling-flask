import os

from selenium.webdriver.common.by import By

from .base import LoggedInFunctionalTest


class UploadTest(LoggedInFunctionalTest):
  def test_can_upload_activity(self):
    # From the admin page, the user navigates to the file upload dashboard.
    self.wait_for_element(
      By.XPATH,
      '//*[text()="Analyze Activity File"]'
    ).click()

    # They use the upload widget to select an activity file to analyze.
    input = self.wait_for_element(By.XPATH, '//*[@id="upload-data"]/div/input')
    input.send_keys(
      os.path.join(os.path.dirname(__file__), 'testdata.tcx')
    )

    # The page updates into a full activity analysis dashboard.
    input = self.wait_for_element(
      By.XPATH,
      '//input[contains(@id, \'"subcomponent":"tss"\')]'
    )
    tss = input.get_attribute('value')
    self.assertRegex(tss, r'^[0-9].*\.[0-9]$')