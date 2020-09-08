import unittest
from datetime import time, timedelta, datetime

import pytz

from two_stops_model import *

class TestModels(unittest.TestCase):
	def test_linear_model(self):
		lin_model = Two_stops_model.Linear_model(1000)
		timezone = pytz.timezone("Europe/Prague")
		morning = timezone.localize(datetime(2020, 2, 23, 10, 0, 0).replace(microsecond=0))
		midnight = timezone.localize(datetime(2020, 2, 23, 0, 0, 0).replace(microsecond=0))

		# simple test
		self.assertEqual(0,    lin_model.predict(500, morning, timedelta(hours=9, minutes=50, seconds=0), timedelta(hours=10, minutes=10, seconds=0)))
		self.assertEqual(-300, lin_model.predict(750, morning, timedelta(hours=9, minutes=50, seconds=0), timedelta(hours=10, minutes=10, seconds=0)))
		self.assertEqual(600, lin_model.predict(0, morning, timedelta(hours=9, minutes=50, seconds=0), timedelta(hours=10, minutes=10, seconds=0)))

		# midnight tests
		self.assertEqual(0, lin_model.predict(500, midnight, timedelta(hours=23, minutes=50, seconds=0), timedelta(hours=0, minutes=10, seconds=0)))
		self.assertEqual(-300, lin_model.predict(750, midnight, timedelta(hours=23, minutes=50, seconds=0), timedelta(hours=0, minutes=10, seconds=0)))
		self.assertEqual(600, lin_model.predict(0, midnight, timedelta(hours=23, minutes=50, seconds=0), timedelta(hours=0, minutes=10, seconds=0)))
		self.assertEqual(480, lin_model.predict(0, timezone.localize(datetime(2020, 2, 22, 23, 58, 0).replace(microsecond=0)), timedelta(hours=23, minutes=50, seconds=0), timedelta(hours=0, minutes=10, seconds=0)))


if __name__ == '__main__':
	unittest.main()
