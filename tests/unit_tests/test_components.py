import unittest

from distilling_flask.plotlydash.aio_components import TimeInput


class TestTimeInput(unittest.TestCase):
  def test_no_input(self):
    self.assertEqual(TimeInput().value, '00:00:00')

  def test_handles_decimal(self):
    self.assertEqual(TimeInput(seconds=0.1).value, '00:00:00')

  def test_rounds_up(self):
    self.assertEqual(TimeInput(seconds=0.6).value, '00:00:01')

  def test_no_60_seconds(self):
    self.assertEqual(TimeInput(seconds=59.6).value, '00:01:00')
