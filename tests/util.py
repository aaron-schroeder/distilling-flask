import json
import os
import time

from flask import url_for
from selenium import webdriver
from selenium.common.exceptions import (
  ElementClickInterceptedException,
  NoSuchElementException,
  WebDriverException
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


MAX_WAIT = 10


def get_chromedriver():
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
  return webdriver.Chrome(
    service=s,
    options=chrome_options
  )


def load_strava_credentials():
  # path = os.path.dirname(os.path.realpath(__file__))
  # with open(os.path.join(path, 'strava_credentials.json'), 'r') as f:
  with open('tests/functional_tests/strava_credentials.json', 'r') as f:
    credentials = json.load(f)
  return credentials


def wait_for_element(browser, by, value):
  start_time = time.time()
  while True:
    try:
      return browser.find_element(by, value)
    except WebDriverException as e:
      if time.time() - start_time > MAX_WAIT:
        with open('out.html', 'w') as f:
          f.write(browser.page_source)
        raise e
      time.sleep(0.5)


def strava_auth_flow(browser):
  credentials = load_strava_credentials()

  un = browser.find_element(By.ID, 'email')
  un.clear()
  un.send_keys(credentials['USERNAME'])
  pw = browser.find_element(By.ID, 'password')
  pw.clear()
  pw.send_keys(credentials['PASSWORD'])
  browser.find_element(By.ID, 'login-button').click()

  try:
    auth_btn = browser.find_element(By.ID, 'authorize')
  except:
    try:
      print(browser.find_element(By.CLASS_NAME, 'alert-message').text)
    except:
      print(browser.page_source)

  # A cookie banner may be in the way
  try:
    auth_btn.click()
  except ElementClickInterceptedException:
    browser.find_element(
      By.CLASS_NAME, 
      'btn-accept-cookie-banner'
    ).click()
    auth_btn.click()


def expand_dash_err_container(browser):
  browser.find_element(By.CLASS_NAME, 'dash-error-card__list-item').click()