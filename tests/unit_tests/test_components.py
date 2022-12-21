import unittest

from application.plotlydash.aio_components import TimeInputAIO


class TestTimeInput(unittest.TestCase):
  def test_no_input(self):
    self.assertEqual(TimeInputAIO().value, '00:00:00')

  def test_handles_decimal(self):
    self.assertEqual(TimeInputAIO(seconds=0.1).value, '00:00:00')

  def test_rounds_up(self):
    self.assertEqual(TimeInputAIO(seconds=0.6).value, '00:00:01')
