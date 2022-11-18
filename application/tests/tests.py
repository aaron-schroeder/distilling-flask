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
  
  @classmethod
  def setUpClass(cls):
    """
    Refs:
      https://coddyschool.com/upload/Flask_Web_Development_Developing.pdf#page=221
      https://stackoverflow.com/questions/60111814/flask-application-was-not-able-to-create-a-url-adapter-for-request
    """
    # cls.app = create_app('testing')
    cls.app = create_app(test_config={
      'TESTING': True,
      'SQLALCHEMY_DATABASE_URI': os.environ.get(
        'TEST_DATABASE_URL',
        'sqlite:///' + os.path.join(BASEDIR, 'data-test.sqlite')
      )
    })
    cls.app_context = cls.app.app_context()
    cls.app_context.push()
    cls.request_context = cls.app.test_request_context()
    cls.request_context.push()
    # db.create_all()  # happens in `create_app()`
    cls.client = cls.app.test_client(use_cookies=True)

  @classmethod
  def tearDownClass(cls):
    db.session.remove()
    db.drop_all()
    cls.app_context.pop()
    cls.request_context.pop()

  def test_home_page_returns_correct_html(self):
    response = self.client.get('/')

    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Welcome - Training Zealot</title>', html)
