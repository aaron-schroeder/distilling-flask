import unittest


class StravaPageTest(unittest.TestCase):
  # TODO: Figure out how to test a specific dash page, typ.

  def test_duplicate_activity_isnt_saved(self):
    # self.client.post('/lists/new', data={'item_text': ''})
    # self.assertEqual(List.objects.count(), 0)
    # self.assertEqual(Item.objects.count(), 0)
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