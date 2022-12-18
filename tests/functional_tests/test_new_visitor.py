"""
Refs:
  https://www.obeythetestinggoat.com/book/chapter_01.html
  https://stackoverflow.com/questions/64717302/deprecationwarning-executable-path-has-been-deprecated-selenium-python
  https://www.obeythetestinggoat.com/book/chapter_02_unittest.html
"""
import os
from urllib.parse import urljoin

from selenium.webdriver.common.by import By

from .base import FunctionalTest


class NewVisitorTest(FunctionalTest):

  def test_can_see_landing_page(self):

    # Edith has heard about a cool new online to-do app. She goes
    # to check out its homepage.
    self.browser.get(self.server_url)

    # She notices the page title and header welcomes her to
    # the app and tells her its name.
    self.assertIn('Welcome - Training Zealot', self.browser.title)
    header_text = self.browser.find_element(By.TAG_NAME, 'h2').text
    self.assertIn('Welcome', header_text)
    
    # She sees a navigation bar that takes her back to the app's home page.
    navbar = self.browser.find_element(
      By.XPATH,
      '//nav[contains(@class, "navbar")]/a[contains(@class, "navbar-brand")]'
    )
    self.assertIn('The Training Zealot Analysis Platform', navbar.text)
    self.assertEqual(
      navbar.get_attribute('href'),
      urljoin(self.server_url, '/')
    )

    # She sees links inviting her to visit a list of her Strava activities...
    self.check_for_link_text('Strava activities')

    # ...a training log dashboard...
    self.check_for_link_text('Training log dashboard')

    # ...and a file analysis dashboard.
    self.check_for_link_text('Analyze an activity file (.gpx, .fit, .tcx, .csv)')

    # Satisfied, she goes back to sleep

  def test_can_upload_activity(self):
    # From the landing page, the user navigates to the file upload dashboard.
    self.browser.get(self.server_url)
    self.browser.find_element(
      By.PARTIAL_LINK_TEXT,
      'Analyze an activity file'
    ).click()

    # They use the upload widget to select an activity file to analyze.
    input = self.wait_for_element(By.XPATH, '//*[@id="upload-data"]/div/input')
    input.send_keys(
      os.path.join(os.path.dirname(__file__), 'testdata.tcx')
    )

    # The page updates into a full activity analysis dashboard.
    input = self.wait_for_element(By.XPATH, '//input[contains(@id, "tss")]')
    tss = input.get_attribute('value')
    self.assertRegex(tss, r'^[0-9].*\.[0-9]$')

