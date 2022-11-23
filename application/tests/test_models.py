from application.models import Activity
from .base import FlaskTestCase


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
