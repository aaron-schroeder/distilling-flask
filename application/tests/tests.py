"""
Ref:
  https://www.obeythetestinggoat.com/book/chapter_unit_test_first_view.html
"""
import datetime
import os
import unittest

from flask import url_for

from application import create_app, db
from application.models import Activity


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


class ActivityModelTest(unittest.TestCase):

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
    self.client = self.app.test_client(use_cookies=True)
    self.app_context = self.app.app_context()
    self.app_context.push()

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    self.app_context.pop()

  def test_saving_and_retrieving_items(self):
    first_act = Activity(
      title='The first (ever) Activity item',
      description='description',
      created=datetime.datetime.utcnow(),
      recorded=datetime.datetime.utcnow(),
      tz_local='UTC',
      moving_time_s=3600,
      elapsed_time_s=3660,
      filepath_orig='activity_1.tcx',
      filepath_csv='activity_1.tcx',
      # Fields below here not required
      # strava_id=activity_data['id'],
      # distance_m=activity_data['distance'],
      # elevation_m=activity_data['total_elevation_gain'],
      # intensity_factor=intensity_factor,
      # tss=tss,
    )
    db.session.add(first_act)
    db.session.commit()

    second_act = Activity(
      title='Activity the second',
      description='description',
      created=datetime.datetime.utcnow(),
      recorded=datetime.datetime.utcnow(),
      tz_local='UTC',
      moving_time_s=3600,
      elapsed_time_s=3660,
      filepath_orig='activity_2.tcx',
      filepath_csv='activity_2.tcx',
    )
    db.session.add(second_act)
    db.session.commit()

    saved_items = Activity.query.all()
    self.assertEqual(len(saved_items), 2)

    first_saved_item = saved_items[0]
    second_saved_item = saved_items[1]
    self.assertEqual(first_saved_item.title, 'The first (ever) Activity item')
    self.assertEqual(second_saved_item.title, 'Activity the second')