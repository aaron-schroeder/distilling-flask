import unittest

from distilling_flask.io_storages.strava.util import est_15_min_rate
from distilling_flask.util.mock_stravalib import SimDevClient, SimProdClient


class TestEstRate(unittest.TestCase):
  def test_low_limit(self):
    self.assertEqual(
      est_15_min_rate(SimDevClient()),
      3)

  def test_high_limit(self):
    self.assertEqual(
      est_15_min_rate(SimProdClient()),
      104)

  @unittest.skip('estimator function is not yet sophisticated enough')
  def test_high_limit_w_usage(self):
    self.assertEqual(
      est_15_min_rate(SimProdClient(
        # short_limit=600,
        # short_usage=0,
        # long_limit=30000,
        # long_usage=15000,
      )),
      52)