import json
import os

from selenium.common import exceptions
from selenium.webdriver.common.by import By

from .base import FunctionalTest


class StravaAuthTest(FunctionalTest):
  def setUp(self):
    super().setUp()
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, 'strava_credentials.json'), 'r') as f:
      self.credentials = json.load(f)

  def test_can_authorize(self):
    self.browser.get(self.server_url)
    self.browser.find_element(By.LINK_TEXT, 'Strava activities').click()
    
    un = self.wait_for_element(By.ID, 'email')
    un.clear()
    un.send_keys(self.credentials['USERNAME'])
    pw = self.wait_for_element(By.ID, 'password')
    pw.clear()
    pw.send_keys(self.credentials['PASSWORD'])
    self.browser.find_element(By.ID, 'login-button').click()

    auth_btn = self.wait_for_element(By.ID, 'authorize')

    # A cookie banner may be in the way
    try:
      auth_btn.click()
    except exceptions.ElementClickInterceptedException:
      self.browser.find_element(
        By.CLASS_NAME, 
        'btn-accept-cookie-banner'
      ).click()
      auth_btn.click()

    self.assertIn(
      'Strava activities',
      self.browser.find_element(By.TAG_NAME, 'h2').text
    )