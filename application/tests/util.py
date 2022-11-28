from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


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
