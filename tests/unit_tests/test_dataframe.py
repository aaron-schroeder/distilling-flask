import datetime
import unittest

from dateutil import tz
import pandas as pd

from application.util.dataframe import calc_ctl_atl


class TestCalcCtlAtl(unittest.TestCase):
  def test_adds_current_val(self):
    n = 5

    df = pd.DataFrame.from_records([
      {
        'recorded': pd.Timestamp.now(tz.gettz('America/Denver')) - datetime.timedelta(days=i),
        'tss': 100.0
      }
      for i in range(n)
    ])

    result = calc_ctl_atl(df, 4.0)

    self.assertIsInstance(result, pd.DataFrame)
    self.assertEqual(len(result), n + 1)

    for col in ['ATL_pre', 'CTL_pre', 'ATL_post', 'CTL_post']:
      self.assertIn(col, result.columns)

  def test_fills_empty_days(self):
    n = 5

    df = pd.DataFrame.from_records([
      {
        'recorded': pd.Timestamp.now(tz.gettz('America/Denver')) - datetime.timedelta(days=2*i),
        'tss': 100.0
      }
      for i in range(n)
    ])

    result = calc_ctl_atl(df, 4.0)

    self.assertEqual(len(result), 2 * n)
    self.assertEqual((result['tss'].iloc[1::2] == 0.0).sum(), n)
