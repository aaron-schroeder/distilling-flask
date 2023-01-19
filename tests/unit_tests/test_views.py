from flask import url_for

from .base import FlaskTestCase, LoggedInFlaskTestCase


class SettingsPageTest(LoggedInFlaskTestCase):

  def test_settings_page_returns_correct_html(self):
    response = self.client.get(url_for('main.settings'))

    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Profile Settings - Training Zealot</title>', html)
