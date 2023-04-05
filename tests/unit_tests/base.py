"""
Ref:
  https://www.obeythetestinggoat.com/book/chapter_unit_test_first_view.html
"""
import os
import unittest

from distilling_flask import create_app, db


BASEDIR = os.path.abspath(os.path.dirname(__file__))


class FlaskTestCase(unittest.TestCase):
  def setUp(self):
    """
    Refs:
      https://coddyschool.com/upload/Flask_Web_Development_Developing.pdf#page=221
      https://stackoverflow.com/questions/60111814
    """
    self.app = create_app(config_name='test')
    # self.app.test_client_class = FlaskLoginClient
    self.test_request_context = self.app.test_request_context()
    self.test_request_context.push()
    self.app_context = self.app.app_context()
    self.app_context.push()
    self.client = self.app.test_client(use_cookies=True)
    db.create_all()

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    self.app_context.pop()
    self.test_request_context.pop()
