import unittest
from datetime import time, timedelta, datetime
from statistics import mean, variance

import pytz

from database import Database
from two_stops_model import *

class TestNormData(unittest.TestCase):
	def test_init_and_basics(self):
		dt_morning = timedelta(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]
		ids_trip = [1, 1, 1, 2, 3, 3]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip)

		self.assertListEqual(shapes, nd.get_shapes().tolist())
		self.assertListEqual(day_times, nd.get_day_times().tolist())
		self.assertEqual(6, len(nd))

	def test_iter(self):
		dt_morning = datetime(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]
		ids_trip = [1, 1, 1, 2, 3, 3]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip)

		iterator = iter(nd)
		first = next(iterator)

		self.assertEqual(1, first.shape)
		self.assertEqual(1, first.id_trip)

		second = next(iterator)

		self.assertEqual(2, second.shape)
		self.assertEqual(1, second.id_trip)

	def test_simple_remove_item_by_id_trip(self):
		dt_morning = datetime(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]
		ids_trip = [1, 1, 2, 2, 3, 3]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip)

		nd.remove_items_by_id_trip({2})

		self.assertEqual(5, nd.get_shapes()[2])

	def test_more_remove_item_by_id_trip(self):
		dt_morning = datetime(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]
		ids_trip = [1, 3, 2, 2, 4, 4]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip)

		nd.remove_items_by_id_trip({2, 3})

		self.assertEqual(5, nd.get_shapes()[1])
		self.assertEqual(6, nd.get_shapes()[2])
		self.assertEqual(3, len(nd))



class TestModels(unittest.TestCase):
	def test_linear_model(self):
		lin_model = Two_stops_model.Linear_model(1000)
		# timezone = pytz.timezone("Europe/Prague")
		morning = timedelta(hours=10, minutes=0, seconds=0).seconds
		midnight = timedelta(hours=0, minutes=0, seconds=0).seconds

		# simple test
		self.assertEqual(0,    lin_model.predict(500, morning, timedelta(hours=9, minutes=50, seconds=0).seconds, timedelta(hours=10, minutes=10, seconds=0).seconds))
		self.assertEqual(-300, lin_model.predict(750, morning, timedelta(hours=9, minutes=50, seconds=0).seconds, timedelta(hours=10, minutes=10, seconds=0).seconds))
		self.assertEqual(600, lin_model.predict(0, morning, timedelta(hours=9, minutes=50, seconds=0).seconds, timedelta(hours=10, minutes=10, seconds=0).seconds))

		# midnight tests
		self.assertEqual(0, lin_model.predict(500, midnight, timedelta(hours=23, minutes=50, seconds=0).seconds, timedelta(hours=0, minutes=10, seconds=0).seconds))
		self.assertEqual(-300, lin_model.predict(750, midnight, timedelta(hours=23, minutes=50, seconds=0).seconds, timedelta(hours=0, minutes=10, seconds=0).seconds))
		self.assertEqual(600, lin_model.predict(0, midnight, timedelta(hours=23, minutes=50, seconds=0).seconds, timedelta(hours=0, minutes=10, seconds=0).seconds))
		self.assertEqual(480, lin_model.predict(0, timedelta(hours=23, minutes=58, seconds=0).seconds, timedelta(hours=23, minutes=50, seconds=0).seconds, timedelta(hours=0, minutes=10, seconds=0).seconds))

	def test_poly_model_a(self):
		model = File_system.pickle_load_object(Path('../input_data') / Path("221406_223778_hol.model"))
		data = File_system.pickle_load_object(Path('../input_data') / Path("221406_223778_hol.data"))

		linear_delay = []
		last_stop_delay = []
		model_delay = []
		next_stop_delay = []
		diff_model = []
		diff_linear = []

		database_connection = Database('vehicle_positions_database')


		i = 0
		for row in data:
			i += 1
			linear_delay.append(Two_stops_model.Linear_model(row[5]).predict(row[7],
				timedelta(hours=row[6].hour, minutes=row[6].minute, seconds=row[6].second).seconds,
				row[3].seconds,
				row[4].seconds,))
			last_stop_delay.append(row[8])

			model_delay.append(model.predict(
				row[7],
				timedelta(hours=row[6].hour, minutes=row[6].minute, seconds=row[6].second).seconds,
				row[3].seconds,
				row[4].seconds,
			))

			next_stop_delay.append(database_connection.execute_fetchall("""
				select last_stop_delay
				from trip_coordinates 
				where shape_dist_traveled > (
					select shape_dist_traveled 
					from rides 
					where id_trip = %s and id_stop = %s
				)
				and id_trip = %s and inserted BETWEEN %s AND %s order by shape_dist_traveled LIMIT 1;""",
				(row[0], row[2], row[0], row[6], row[6] + timedelta(hours=1))
			)[0][0])

			diff_model.append(next_stop_delay[-1]-model_delay[-1])
			diff_linear.append(next_stop_delay[-1] - linear_delay[-1])

		# arr = np.array((linear_delay, last_stop_delay, model_delay, next_stop_delay, diff_model, diff_linear))

		# poly model should always give lower mean and variance than linear model

		self.assertAlmostEqual(7.4, mean(diff_model), delta=1.0)
		self.assertAlmostEqual(3051.9, variance(diff_model), delta=1.0)

		self.assertAlmostEqual(-69.2, mean(diff_linear), delta=1.0)
		self.assertAlmostEqual(4973.9, variance(diff_linear), delta=1.0)

		print("Model Mean:", mean(diff_model), "Variance:", variance(diff_model))
		print("Linear Mean:", mean(diff_linear), "Variance:", variance(diff_linear))


if __name__ == '__main__':
	unittest.main()
