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

    # Edith has heard about a cool training log app.
    # She goes to check out its homepage.
    self.browser.get(self.server_url)

    # She notices the page title and header welcomes her to
    # the app and tells her its name.
    self.assertIn('Welcome - Training Zealot', self.browser.title)
    header_text = self.browser.find_element(By.TAG_NAME, 'h2').text
    self.assertIn('Training Log', header_text)
    
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

    # She sees a graph of Aaron's training stress over time...

    # ...and a calendar view of his training log.

    # Satisfied, she goes back to sleep


  def test_can_view_activity(self):
    # A user visits the main page of the app - a training log.

    # She notices that the individual activities in the training log are clickable.
    
    # She clicks one and is taken to an activity analysis page.

    pass