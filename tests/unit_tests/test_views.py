from .base import FlaskTestCase


class HomePageTest(FlaskTestCase):

  def test_home_page_returns_correct_html(self):
    response = self.client.get('/')

    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Welcome - Training Zealot</title>', html)


class ListPageTest(FlaskTestCase):
  
  def test_displays_all_list_items(self):
    self.create_activity(title='itemey 1')
    self.create_activity(title='itemey 2')

    response = self.client.get('/view-saved-activities')

    self.assertIn('itemey 1', response.get_data(as_text=True))
    self.assertIn('itemey 2', response.get_data(as_text=True))