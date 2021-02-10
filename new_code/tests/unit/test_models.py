import unittest
from datetime import time, timedelta, datetime
from statistics import mean, variance

import pytz

import lib
from database import Database
from two_stops_model import *

class TestNormData(unittest.TestCase):
	def test_init_and_basics(self):
		dt_morning = datetime(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [lib.time_to_sec(dt_morning), lib.time_to_sec(dt_morning + hour), lib.time_to_sec(dt_morning + 2 * hour), lib.time_to_sec(dt_morning + 3 * hour), lib.time_to_sec(dt_morning + 4 * hour), lib.time_to_sec(dt_morning + 5 * hour)]
		ids_trip = [1, 1, 1, 2, 3, 3]
		timestamps = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip, timestamps)

		self.assertListEqual(shapes, nd.get_shapes().tolist())
		self.assertListEqual(day_times, nd.get_day_times().tolist())
		self.assertEqual(6, len(nd))

	def test_iter(self):
		dt_morning = datetime(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [lib.time_to_sec(dt_morning), lib.time_to_sec(dt_morning + hour), lib.time_to_sec(dt_morning + 2 * hour), lib.time_to_sec(dt_morning + 3 * hour), lib.time_to_sec(dt_morning + 4 * hour), lib.time_to_sec(dt_morning + 5 * hour)]
		ids_trip = [1, 1, 1, 2, 3, 3]
		timestamps = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip, timestamps)

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
		day_times = [lib.time_to_sec(dt_morning), lib.time_to_sec(dt_morning + hour), lib.time_to_sec(dt_morning + 2 * hour), lib.time_to_sec(dt_morning + 3 * hour), lib.time_to_sec(dt_morning + 4 * hour), lib.time_to_sec(dt_morning + 5 * hour)]
		ids_trip = [1, 1, 1, 2, 3, 3]
		timestamps = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip, timestamps)

		nd.remove_items_by_id_trip({2}, dict([(2, [dt_morning + 3 * hour])]))

		self.assertEqual(5, nd.get_shapes()[3])

	def test_more_remove_item_by_id_trip(self):
		dt_morning = datetime(2020, 2, 20, 1, 0, 0)
		hour = timedelta(hours=1)
		minute = timedelta(minutes=1)

		shapes = [1, 2, 3, 4, 5, 6]
		coor_times = [minute, minute * 2, minute * 3, minute * 4, minute * 5, minute * 6]
		day_times = [lib.time_to_sec(dt_morning), lib.time_to_sec(dt_morning + hour), lib.time_to_sec(dt_morning + 2 * hour), lib.time_to_sec(dt_morning + 3 * hour), lib.time_to_sec(dt_morning + 4 * hour), lib.time_to_sec(dt_morning + 5 * hour)]
		ids_trip = [1, 1, 1, 2, 3, 3]
		timestamps = [dt_morning, dt_morning + hour, dt_morning + 2 * hour, dt_morning + 3 * hour, dt_morning + 4 * hour, dt_morning + 5 * hour]

		nd = Norm_data(shapes, coor_times, day_times, ids_trip, timestamps)

		nd.remove_items_by_id_trip({2, 1}, dict([(2, [dt_morning]), (1, [dt_morning - timedelta(days=1), dt_morning + 3 * hour, dt_morning + 4 * hour])]))

		self.assertEqual(2, nd.get_shapes()[1])
		self.assertEqual(4, nd.get_shapes()[2])
		self.assertEqual(5, len(nd))


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
		model = File_system.pickle_load_object(Path('../input_data') / Path("2_2374_hol.model"))
		data = File_system.pickle_load_object(Path('../input_data') / Path("2_2374_hol.data"))

		linear_delay = []
		last_stop_delay = []
		model_delay = []
		next_stop_delay = []
		diff_model = []
		diff_linear = []

		database_connection = Database('vehicle_positions_database')

		# i = 0
		for row in data:
			# i += 1
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

		self.assertAlmostEqual(3.9, mean(diff_model), delta=5.0)
		self.assertAlmostEqual(3067.9, variance(diff_model), delta=50.0)

		self.assertAlmostEqual(-69.2, mean(diff_linear), delta=1.0)
		self.assertAlmostEqual(4973.9, variance(diff_linear), delta=1.0)

		print("Model Mean:", mean(diff_model), "Variance:", variance(diff_model))
		print("Linear Mean:", mean(diff_linear), "Variance:", variance(diff_linear))

	def test_train_model(self):
		pass



class TestTwo_stops_models(unittest.TestCase):
	def test_add_row_a(self):
		database_connection = Database('vehicle_positions_database')

		# demo app needs aprox 30 secs to fetch
		# in production it may takes longer time to fetch all data
		database_connection.execute('SET GLOBAL connect_timeout=600')
		database_connection.execute('SET GLOBAL wait_timeout=600')
		database_connection.execute('SET GLOBAL interactive_timeout=600')

		stop_to_stop_data = database_connection.execute_procedure_fetchall(
			'get_all_pairs_of_stops', (0, 0, 1500))

		res_list = []
		shapes = []
		coor_times = []

		cur_dep_stop = stop_to_stop_data[0][1]
		cur_arr_stop = stop_to_stop_data[0][2]
		no_of_samples = 0
		rows_to_save = []

		for row in stop_to_stop_data:
			if row[1] == 9167 and row[2] == 5221:
				rows_to_save.append(row)
			if cur_dep_stop == row[1] and cur_arr_stop == row[2]:
				if row[7] != 0:
					no_of_samples += 1
					shapes.append(row[7])
					coor_times.append(Two_stops_model._get_coor_time(lib.time_to_sec(row[6]), row[3].seconds, row[8]))

			else:
				rate = np.divide(coor_times, np.divide(shapes, 10))

				res_list.append([cur_dep_stop, cur_arr_stop, np.nanmean(rate), no_of_samples])
				# high_variable = np.where(abs(rate - rate.mean()) > rate.std() is True)
				if row[7] != 0:
					coor_times=[]
					shapes=[]
					shapes.append(row[7])
					coor_times.append(Two_stops_model._get_coor_time(lib.time_to_sec(row[6]), row[3].seconds, row[8]))

					no_of_samples = 1

				cur_dep_stop = row[1]
				cur_arr_stop = row[2]

		rate = np.divide(coor_times, np.divide(shapes, 10))

		res_list.append([cur_dep_stop, cur_arr_stop, np.nanmean(rate), no_of_samples])

		res_arr = np.array(res_list)

		File_system.pickle_object(rows_to_save, '../input_data/test_two_stops_model_data.list')

		rows = File_system.pickle_load_object('../input_data/test_two_stops_model_data.list')

		model = Two_stops_model(rows[0][1], rows[0][2], rows[0][5], 'bss')

		for row in rows:
			model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])
			# print(row[4].seconds - row[3].seconds)

		self.assertEqual(240, model.max_travel_time)
		self.assertEqual(36, len(model.shapes))


	def test_add_row_b(self):
		rows: list = File_system.pickle_load_object('../input_data/test_two_stops_model_data.list')

		# midnight bus
		rows.append((47891, 230571, 226625, timedelta(hours=23, minutes=57, seconds=0), timedelta(hours=0, minutes=3, seconds=0), 1914, datetime(2020, 2, 20, 23, 59, 0), 96, 111, 113))

		model = Two_stops_model(rows[0][1], rows[0][2], rows[0][5], 'bss')

		for row in rows:
			model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])
			# print(row[4].seconds - row[3].seconds)

		self.assertEqual(360, model.max_travel_time)
		self.assertEqual(37, len(model.shapes))


	def test_add_row_c(self):
		rows: list = File_system.pickle_load_object('../input_data/test_two_stops_model_data.list')

		# midnight bus
		rows.append((47891, 230571, 226625, timedelta(hours=23, minutes=57, seconds=0), timedelta(hours=0, minutes=3, seconds=0), 1914, datetime(2020, 2, 20, 0, 1, 0), 96, 111, 113))

		model = Two_stops_model(rows[0][1], rows[0][2], rows[0][5], 'bss')

		for row in rows:
			model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])


		self.assertEqual(360, model.max_travel_time)
		self.assertEqual(37, len(model.shapes))

	def test_add_row_d(self):
		rows: list = File_system.pickle_load_object('../input_data/test_two_stops_model_data.list')

		# midnight bus
		rows.append((47891, 230571, 226625, timedelta(hours=23, minutes=57, seconds=0), timedelta(hours=0, minutes=3, seconds=0), 1914, datetime(2020, 2, 20, 23, 56, 0), 96, 111, 113))

		model = Two_stops_model(rows[0][1], rows[0][2], rows[0][5], 'bss')

		for row in rows:
			model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])
			# print(row[4].seconds - row[3].seconds)

		self.assertEqual(360, model.max_travel_time)
		self.assertEqual(37, len(model.shapes))

	def test_get_coor_time(self):
		dep = timedelta(hours=23, minutes=57, seconds=0).seconds
		day_time_a = lib.time_to_sec(datetime(2020, 2, 20, 23, 59, 0))
		day_time_b = lib.time_to_sec(datetime(2020, 2, 20, 0, 1, 0))

		self.assertEqual(90, Two_stops_model._get_coor_time(day_time_a, dep, 30))
		self.assertEqual(210, Two_stops_model._get_coor_time(day_time_b, dep, 30))

	def test_reduce_errors(self):
		rows: list = File_system.pickle_load_object('../input_data/test_two_stops_model_data.list')
		model = Two_stops_model(rows[0][1], rows[0][2], rows[0][5], 'bss')

		for row in rows:
			model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])

		model.norm_data = Norm_data(model.shapes, model.coor_times, model.day_times, model.ids_trip, model.timestamps)

		self.assertEqual(36, len(model.norm_data))

		model._reduce_errors()

		self.assertEqual(36, len(model.norm_data))

		# super delayed row
		row = (47891, 230571, 226625, timedelta(seconds=49260), timedelta(seconds=49500), 1914, datetime(2020, 2, 23, 13, 45, 5), 1196, 2000, 104)
		model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])
		model.norm_data = Norm_data(model.shapes, model.coor_times, model.day_times, model.ids_trip, model.timestamps)

		# deletes one sample
		model._reduce_errors()

		self.assertEqual(36, len(model.norm_data))

	def test_create_model(self):
		rows: list = File_system.pickle_load_object('../input_data/test_two_stops_model_data.list')
		model = Two_stops_model(rows[0][1], rows[0][2], rows[0][5], 'bss')

		for row in rows:
			model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])

		# creates linear model because not enough data samples
		model.create_model()

		self.assertIsInstance(model.model, Two_stops_model.Linear_model)

		# add more data samples
		for _ in range(4):
			for row in rows:
				model.add_row(row[7], row[3].seconds, row[6], row[0], row[4].seconds, row[8])

		model.create_model()

		self.assertIsInstance(model.model, Two_stops_model.Polynomial_model)



if __name__ == '__main__':
	unittest.main()
