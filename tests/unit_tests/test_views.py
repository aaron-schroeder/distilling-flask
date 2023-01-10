from flask import url_for

from .base import FlaskTestCase, LoggedInFlaskTestCase


class AdminLandingPageTest(LoggedInFlaskTestCase):

  def test_admin_page_returns_correct_html(self):
    response = self.client.get(url_for('route_blueprint.admin_landing'))

    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Admin - Training Zealot</title>', html)


class ListPageTest(FlaskTestCase):
  
  def test_displays_all_list_items(self):
    self.create_activity(title='itemey 1')
    self.create_activity(title='itemey 2')

    response = self.client.get(url_for('route_blueprint.view_activities'))

    self.assertIn('itemey 1', response.get_data(as_text=True))
    self.assertIn('itemey 2', response.get_data(as_text=True))