import datetime
import unittest

import pandas as pd

from application.util.dataframe import calc_ctl_atl


class TestCalcCtlAtl(unittest.TestCase):
  def test_basic(self):
    df = pd.DataFrame.from_records([
      {
        'recorded': datetime.datetime.now() - datetime.timedelta(days=i),
        'tss': 100.0
      }
      for i in range(5)
    ])

    result = calc_ctl_atl(df)

    self.assertIsInstance(result, pd.DataFrame)

    for col in ['ATL_pre', 'CTL_pre', 'ATL_post', 'CTL_post']:
      self.assertIn(col, df.columns)

  def test_fills_empty_days(self):
    df = pd.DataFrame.from_records([
      {
        'recorded': datetime.datetime.now() - datetime.timedelta(days=2*i),
        'tss': 100.0
      }
      for i in range(5)
    ])

    result = calc_ctl_atl(df)

    self.assertEqual(len(result), 9)
    self.assertEqual(
      (result['tss'].iloc[:2:] == 0.0).sum,
      4
    )
