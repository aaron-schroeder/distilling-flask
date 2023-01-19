"""Test tasks with mocked-out stravalib Client

Things required by each test:
- db containing a StravaAccount with dummy strava stuff
- Access to the ID of that dummy acct
- stravalib client swapped for mock_stravalib Client in ANY code that is
  triggered by the code under test.

"""
import unittest

from application.tasks import est_15_min_rate
from application.util.mock_stravalib import SimDevClient, SimProdClient


class TestEstRate(unittest.TestCase):
    
  def test_low_limit(self):
    self.assertEqual(
      est_15_min_rate(
        SimDevClient()
      ),
      3
    )

  def test_high_limit(self):
    self.assertEqual(
      est_15_min_rate(
        SimProdClient()
      ),
      104
    )

  @unittest.skip('estimator function is not yet sophisticated enough')
  def test_high_limit_w_usage(self):
    self.assertEqual(
      est_15_min_rate(
        SimProdClient(
          # short_limit=600,
          # short_usage=0,
          # long_limit=30000,
          # long_usage=15000,
        )
      ),
      52
    )