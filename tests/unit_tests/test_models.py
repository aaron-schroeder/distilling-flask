from distilling_flask import db
from distilling_flask.models import AdminUser, UserSettings
from tests.unit_tests.base import FlaskTestCase


class AdminUserModelTest(FlaskTestCase):

  def test_user_is_valid_with_id_only(self):
    user = AdminUser()  # should not raise
    self.assertIsNotNone(user.id)
  
  def test_id_is_always_same(self):
    user_1 = AdminUser()
    user_2 = AdminUser()
    self.assertEqual(user_1.id, 1)
    self.assertEqual(user_2.id, 1)
