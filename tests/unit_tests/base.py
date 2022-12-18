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
        # 'sqlite:///' + os.path.join(BASEDIR, 'data-test.sqlite')
        'sqlite://'
      ),
      'SECRET_KEY': 'super secret key'
    })
    self.app_context = self.app.app_context()
    self.app_context.push()
    # self.client.
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
