"""
Refs:
  https://www.obeythetestinggoat.com/book/chapter_01.html
  https://stackoverflow.com/questions/64717302/deprecationwarning-executable-path-has-been-deprecated-selenium-python
  https://www.obeythetestinggoat.com/book/chapter_02_unittest.html
"""
import unittest
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = 'http://localhost:5000'


class NewVisitorTest(unittest.TestCase):
  def setUp(self):
    # Opt 1: Set up and use Firefox webdriver, like in Chapter 1.
    # browser = webdriver.Firefox()

    # Option 2: Use existing Chrome driver setup
    # WSL (Linux) setup
    s = Service(ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    # Note: the following 3 options are necessary to run in WSL.
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    self.browser = webdriver.Chrome(
      service=s,
      options=chrome_options
    )

  def tearDown(self):
    self.browser.quit()

  def check_for_link_text(self, link_text):
    self.assertIsNotNone(
      self.browser.find_element(By.LINK_TEXT, link_text))

  def test_can_see_landing_page(self):

    # Edith has heard about a cool new online to-do app. She goes
    # to check out its homepage.
    self.browser.get(BASE_URL)

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
    self.assertEqual(navbar.get_attribute('href'), urljoin(BASE_URL, '/'))

    # She sees links inviting her to visit a list of her Strava activities...
    self.check_for_link_text('Strava activities')

    # ...a training log dashboard...
    self.check_for_link_text('Training log dashboard')

    # ...and a file analysis dashboard.
    self.check_for_link_text('Analyze an activity file (.gpx, .fit, .tcx, .csv)')

    self.fail('Finish the test!')

    # She clicks a link to visit the page for activity file analysis.
    
    # There is a widget to upload her activity file

    # Satisfied, she goes back to sleep


if __name__ == '__main__':
  unittest.main()