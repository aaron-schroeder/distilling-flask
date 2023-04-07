import json
import unittest
from unittest import mock

import requests
import responses

from distilling_flask.io_storages.strava.util import StravaRateLimitMonitor, StravaApiClient, StravaOauthClient
from distilling_flask.io_storages.strava.util_v1 import est_15_min_rate
from distilling_flask.util.feature_flags import flag_set
from distilling_flask.util.mock_stravalib import SimDevClient, SimProdClient


if flag_set('ff_rename'):
  class StravaClientBaseTest(unittest.TestCase):
    def test_build_url(self):
      sample_url = 'https://www.example.com/'
      for base_url in [
        sample_url, 
        sample_url + 'foo/',
        sample_url + 'foo/bar/'
      ]:
        for rel_url in [
          'foo', 
          'foo/bar'
        ]:
          mock_self = mock.Mock(_base=base_url)
          expected = base_url + rel_url
          for rel_url in [rel_url, '/' + rel_url + '/', 
                          rel_url + '/', '/' + rel_url]:
            result = StravaOauthClient.build_url(mock_self, rel_url)
            self.assertEqual(result, expected)


  class StravaOauthClientTest(unittest.TestCase):
    pass


  class StravaApiClientTest(unittest.TestCase):
    def test_get_streams(self):
      relative_url = ('/activities/1/streams/time,latlng,distance,altitude,'
        'velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth')
      with responses.RequestsMock() as api_mock:
        api_mock.get(StravaApiClient._base + relative_url,
                     headers={'X-Ratelimit-Limit': '100,1000',
                              'X-Ratelimit-Usage': '0,0'})
        _ = StravaApiClient().get(relative_url)

    def test_get_activity_summary(self):
      relative_url = '/activities/1'
      with responses.RequestsMock() as api_mock:
        api_mock.get(StravaApiClient._base + relative_url,
                     headers={'X-Ratelimit-Limit': '100,1000',
                              'X-Ratelimit-Usage': '0,0'})
        _ = StravaApiClient().get(relative_url)  # , include_all_efforts=True)

    def test_short_rate_limit_exceeded(self):
      relative_url = '/'
      with responses.RequestsMock() as api_mock:
        api_mock.get(StravaApiClient._base + relative_url,
                     status=429, headers={'X-Ratelimit-Limit': '100,1000',
                                          'X-Ratelimit-Usage': '101,101'})
        _ = StravaApiClient().get(relative_url)  # , include_all_efforts=True)

  class StravaRateLimitMonitorTest(unittest.TestCase):
    def create_mock_response(self, short_limit, long_limit, short_usage=0, long_usage=0):
      return mock.Mock(headers={
        'X-Ratelimit-Limit': f'{short_limit},{long_limit}',
        'X-Ratelimit-Usage': f'{short_usage},{long_usage}'})
    
    def test_est_rate_low_limit(self):
      mock_resp = self.create_mock_response(100, 1000)
      self.assertEqual(StravaRateLimitMonitor(mock_resp).estimate_max_rate(15), 3)

    def test_est_rate_high_limit(self):
      mock_resp = self.create_mock_response(600, 30000)
      self.assertEqual(StravaRateLimitMonitor(mock_resp).estimate_max_rate(15), 104)

    @unittest.skip('estimator function is not yet sophisticated enough')
    def test_est_rate_high_limit_w_usage(self):
      self.assertEqual(StravaRateLimitMonitor().estimate_max_rate(15), 52)

else:
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