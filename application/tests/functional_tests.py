"""
Refs:
  https://www.obeythetestinggoat.com/book/chapter_01.html
  https://stackoverflow.com/questions/64717302/deprecationwarning-executable-path-has-been-deprecated-selenium-python
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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
browser = webdriver.Chrome(
  service=s,
  options=chrome_options
)

browser.get('http://localhost:5000')

assert 'Welcome - Training Zealot' in browser.title