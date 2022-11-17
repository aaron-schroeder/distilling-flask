"""
Refs:
  https://www.obeythetestinggoat.com/book/chapter_01.html
  https://stackoverflow.com/questions/64717302/deprecationwarning-executable-path-has-been-deprecated-selenium-python
  https://www.obeythetestinggoat.com/book/chapter_02_unittest.html
"""
import unittest

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


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

  def test_can_visit_upload_dashboard(self):

    # Edith has heard about a cool new online to-do app. She goes
    # to check out its homepage.
    self.browser.get('http://localhost:5000')

    # She notices the page title and header welcomes her to
    # the app and tells her its name.
    self.assertIn('Welcome - Training Zealot', self.browser.title)
    self.fail('Finish the test!')

    # She clicks a link to visit a page for activity file analysis.
    
    # There is a widget to upload her activity file

    # Satisfied, she goes back to sleep


if __name__ == '__main__':
  unittest.main()