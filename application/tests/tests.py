"""
Ref:
  https://www.obeythetestinggoat.com/book/chapter_unit_test_first_view.html
"""
import datetime
import os
import unittest

from application import create_app, db
from application.models import Activity


BASEDIR = os.path.abspath(os.path.dirname(__file__))


class FlaskTestCase(unittest.TestCase):
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
    # db.create_all()
    self.client = self.app.test_client(use_cookies=True)

  def tearDown(self):
    db.session.remove()
    db.drop_all()
    self.app_context.pop()

  def create_activity(self, title='title'):
    act = Activity(
      title=title,
      description='description',
      created=datetime.datetime.utcnow(),
      recorded=datetime.datetime.utcnow(),
      tz_local='UTC',
      moving_time_s=3600,
      elapsed_time_s=3660,
      filepath_orig=f'activity_{title}.tcx',
      filepath_csv=f'activity_{title}.csv',
      # Fields below here not required
      # strava_id=activity_data['id'],
      # distance_m=activity_data['distance'],
      # elevation_m=activity_data['total_elevation_gain'],
      # intensity_factor=intensity_factor,
      # tss=tss,
    )
    db.session.add(act)
    db.session.commit()


class HomePageTest(FlaskTestCase):

  def test_home_page_returns_correct_html(self):
    response = self.client.get('/')

    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Welcome - Training Zealot</title>', html)


class ActivityModelTest(FlaskTestCase):

  def test_saving_and_retrieving_items(self):
    self.create_activity(title='The first (ever) Activity item')
    self.create_activity(title='Activity the second')

    saved_items = Activity.query.all()
    self.assertEqual(len(saved_items), 2)

    first_saved_item = saved_items[0]
    second_saved_item = saved_items[1]
    self.assertEqual(first_saved_item.title, 'The first (ever) Activity item')
    self.assertEqual(second_saved_item.title, 'Activity the second')


class ListPageTest(FlaskTestCase):
  def test_displays_all_list_items(self):
    self.create_activity(title='itemey 1')
    self.create_activity(title='itemey 2')

    response = self.client.get('/view-saved-activities')

    self.assertIn('itemey 1', response.get_data(as_text=True))
    self.assertIn('itemey 2', response.get_data(as_text=True))