"""
Ref:
  https://www.obeythetestinggoat.com/book/chapter_unit_test_first_view.html
"""
import os
import unittest

from flask import url_for

from application import create_app, db


BASEDIR = os.path.abspath(os.path.dirname(__file__))


class HomePageTest(unittest.TestCase):
  def setUp(self):
    """
    Refs:
      https://coddyschool.com/upload/Flask_Web_Development_Developing.pdf#page=221
      https://stackoverflow.com/questions/60111814/flask-application-was-not-able-to-create-a-url-adapter-for-request
    """
    # self.app = create_app('testing')
    self.app = create_app(test_config={
      'TESTING': True,
      'SQLALCHEMY_DATABASE_URI': os.environ.get(
        'TEST_DATABASE_URL',
        'sqlite:///' + os.path.join(BASEDIR, 'data-test.sqlite')
      )
    })
    self.app_context = self.app.app_context()
    self.app_context.push()
    self.request_context = self.app.test_request_context()
    self.request_context.push()
    # db.create_all()  # happens in `create_app()`
    self.client = self.app.test_client(use_cookies=True)

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    self.app_context.pop()
    self.request_context.pop()

  def test_root_url_resolves_to_home_page_view(self):
    result = url_for('start_dashapp')
    self.assertEqual(result, '/')

  def test_home_page_returns_correct_html(self):
    response = self.client.get(url_for('start_dashapp'))
    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Welcome - Training Zealot</title>', html)