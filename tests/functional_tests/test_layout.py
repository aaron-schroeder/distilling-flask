from selenium.webdriver.common.by import By
from selenium.webdriver.support.color import Color

from .base import FunctionalTest


class LayoutTest(FunctionalTest):

  def test_layout_and_styling_smoke(self):
    # A user visits the landing page.
    self.browser_get_relative('/')

    # They notice the font family isn't just some plain old default...
    title = self.wait_for_element(By.TAG_NAME, 'h1')
    self.assertNotIn(
      'Times New Roman',
      title.value_of_css_property('font-family').strip()
    )

    # ...and the color is a little more distinguished than plain black.
    self.assertNotEqual(
      Color.from_string(title.value_of_css_property('color')).hex,
      '#000000',
    )