import unittest


class PagesFunctionalTest:
  pass


class StravaPageTest(unittest.TestCase):
  # TODO: Figure out how to test a specific dash page, typ.
  # What I want:
  #  - Do not touch the strava web API (use dummy data)
  #  - Still allow me to drive around the dashboard like in FTs
  #  - The user flows as if they already accepted strava permissions
  # ...answer: (upcoming version of) AuthenticatedUserFunctionalTest
  # ...which requires a refactor of how I store the users' token!
  #    It makes no sense to save in a session value (which goes away
  #    when the user goes to another website or closes the browser)
  #    while providing the user the ability to save items to the DB. 

  def test_duplicate_activity_isnt_saved(self):
    # Try to save a new (duplicate) activity programmatically
    # self.client.post('/lists/new', data={'item_text': ''})

    # Verify that the duplicate Activity was not saved to the DB.
    # self.assertEqual(Activity.objects.count(), 1)

    # ???
    # self.assertNotContains(response, 'other list item 1')
    # self.assertNotContains(response, 'other list item 2')
    pass

  def test_validation_errors_end_up_on_same_page(self):
    # list_ = List.objects.create()
    # response = self.client.post(
    #     f'/lists/{list_.id}/',
    #     data={'item_text': ''}
    # )
    # self.assertEqual(response.status_code, 200)
    # self.assertTemplateUsed(response, 'list.html')
    # expected_error = escape("You can't have an empty list item")
    # self.assertContains(response, expected_error)
    pass