"""Holding area for logic that can only be tested with a live dashboard"""
from flask import url_for
import stravalib
import unittest
from unittest.mock import patch

from distilling_flask.models import db, AdminUser, StravaAccount
from distilling_flask.util.mock_stravalib import (
  MOCK_TOKEN, 
  BatchedResultsIterator as MockBatchIterator
)
from .base import (
  AuthenticatedFlaskTestCase,
  FlaskTestCase,
  LoggedInFlaskTestCase
)


class PagesFunctionalTest:
  pass


@unittest.skip('Needs to be converted to a dash test')
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


@unittest.skip('Needs to be converted to a dash test')
class TestActivityListLoggedIn(LoggedInFlaskTestCase):
  def test_redirect_when_no_token(self):
    for account in AdminUser().strava_accounts:
      self.assertFalse(account.has_authorized)
    
    response = self.client.get(url_for('strava_api.display_activity_list'))
    self.assertEqual(response.status_code, 302)
    self.assertEqual(response.location, url_for('strava_api.authorize'))


@unittest.skip('Needs to be converted to a dash test')
class TestActivityListAuthorized(AuthenticatedFlaskTestCase):
  # @patch('stravalib.Client', mock_stravalib.Client)
  @patch('stravalib.Client.refresh_access_token')
  @patch('stravalib.Client.get_activities')
  @patch('stravalib.Client.get_athlete')
  def test_activity_list(self, mock_athlete, mock_get_activities, mock_refresh_token):

    mock_athlete.return_value = stravalib.model.Athlete(
      firstname='Aaron',
      lastname='Schroeder'
    )
    mock_refresh_token.return_value = MOCK_TOKEN
    mock_get_activities.return_value = MockBatchIterator()

    response = self.client.get(url_for('strava_api.display_activity_list',
      id=self.strava_acct.strava_id))

    self.assertEqual(response.status_code, 200)
    html_data = response.get_data(as_text=True)
    self.assertIn('Activity 1', html_data)
    self.assertIn('Activity 2', html_data)


  @patch('stravalib.Client.refresh_access_token')
  @patch('stravalib.Client.get_activities')
  def test_page_two(self, mock_get_activities, mock_refresh_token):
    mock_refresh_token.return_value = MOCK_TOKEN
    mock_get_activities.return_value = MockBatchIterator()

    response = self.client.get(url_for('strava_api.display_activity_list',
      id=self.strava_acct.strava_id, page=2))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(mock_get_activities.return_value._page, 2)

  def test_no_next_arrow_if_no_next_page(self):
    # Currently would fail.
    # The idea is, if we are at the end of the strava activities,
    # don't provide an option to click over to the next page.
    pass

  def test_token_refreshed_if_expired(self):
    # Might want to just verify that token is passed to refresh_token,
    # and then test refresh_token behavior in test_stravatalk.py
    pass


@unittest.skip('Needs to be converted to a dash test')
class ListPageTest(FlaskTestCase):
  
  def test_displays_all_list_items(self):
    self.create_activity(title='itemey 1')
    self.create_activity(title='itemey 2')

    response = self.client.get(url_for('main.view_activities'))

    self.assertIn('itemey 1', response.get_data(as_text=True))
    self.assertIn('itemey 2', response.get_data(as_text=True))


@unittest.skip('Needs to be converted to a dash test')
class SettingsPageTest(LoggedInFlaskTestCase):

  def test_settings_page_returns_correct_html(self):
    response = self.client.get('/settings')

    html = response.get_data(as_text=True)
    self.assertTrue(html.startswith('<!doctype html>'))
    self.assertIn('<title>Profile Settings - Training Zealot</title>', html)


@unittest.skip('Needs to be converted to a dash test')
class TestManageAccounts(LoggedInFlaskTestCase):
  @patch('stravalib.model.Athlete.stats')
  @patch('stravalib.Client.get_athlete')
  @patch('stravalib.Client.refresh_access_token')
  def test_displays_account_info(self,  mock_refresh_access_token, mock_get_athlete, mock_stats):
    mock_refresh_access_token.return_value = MOCK_TOKEN
    mock_get_athlete.return_value = stravalib.model.Athlete(
      firstname='Aaron',
      lastname='Schroeder',
    )
    mock_stats.return_value = stravalib.model.AthleteStats(
      all_run_totals=stravalib.model.ActivityTotals(count=10)
    )

    db.session.add(StravaAccount(strava_id=1, expires_at=0))
    db.session.commit()
    self.client.get('/settings/strava')

    # TODO: Finish this test
  
  def test_displays_multiple_accounts(self):
    pass