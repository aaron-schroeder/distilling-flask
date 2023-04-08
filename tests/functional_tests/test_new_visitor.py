"""
Refs:
  https://www.obeythetestinggoat.com/book/chapter_01.html
  https://stackoverflow.com/questions/64717302/deprecationwarning-executable-path-has-been-deprecated-selenium-python
  https://www.obeythetestinggoat.com/book/chapter_02_unittest.html
"""
import time
from urllib.parse import urljoin

from selenium.webdriver.common.by import By

from .base import FunctionalTest


class NewUserTest(FunctionalTest):

  def test_can_see_landing_page(self):

    # The user opens the app for the first time.
    self.browser_get_relative('/')

    # TODO: Update this test

    # She notices the page title and header welcomes her to
    # the app and tells her its name.
    time.sleep(2)  # wait a beat for the page to update
    self.assertIn('Training Log Dashboard', self.browser.title)
    header_text = self.browser.find_element(By.TAG_NAME, 'h1').text
    self.assertIn('Training Log', header_text)
    
    # She sees a navigation bar that takes her back to the app's home page.
    navbar = self.browser.find_element(
      By.XPATH,
      '//nav[contains(@class, "navbar")]//a[contains(@class, "navbar-brand")]'
    )
    self.assertIn('Training Zealot Analysis Platform', navbar.text)
    self.assertEqual(
      navbar.get_attribute('href'),
      urljoin(self.server_url, '/')
    )

    # Since the app is just getting started, no activities have been 
    # saved yet.
    self.assertIn('no activities have been saved',
                  self.browser.page_source.lower())

    # TODO: Find a way to pre-populate the server db,
    # so the graph actually displays.

    # She sees a graph of Aaron's training stress over time...

    # ...and a calendar view of his training log.

    # Satisfied, she goes back to sleep


  def test_can_view_activity(self):
    # A user visits the main page of the app - a training log.

    # She notices that the individual activities in the training log are clickable.
    
    # She clicks one and is taken to an activity analysis page.

    pass
  