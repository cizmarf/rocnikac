import unittest

from database import Database
from file_system import File_system
import tests.lib_tests
from stops import Stops


class TestStops(unittest.TestCase):

	def test_insert_ride(self):
		tests.lib_tests.drop_all_tables()
		database_connection = Database('vehicle_positions_test_database')
		vehicle = File_system.pickle_load_object('../input_data/vehicle_test_insert_ride_by_trip.obj')

		vehicle.id_trip = database_connection.execute_fetchall(
			'SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s, %s)',
			vehicle.get_tuple_new_trip(True))[0][0]

		Stops.insert_ride_by_trip(database_connection, vehicle)

		result = database_connection.execute_fetchall('SELECT * FROM rides ORDER BY shape_dist_traveled')

		self.assertEqual(31, len(result))

		self.assertEqual(1, result[0][0])
		self.assertEqual(1, result[0][1])
		self.assertEqual(71400, result[0][2].seconds)
		self.assertEqual(71400, result[0][3].seconds)
		self.assertEqual(0, result[0][4])

	def test_dict_list(self):

		# simple test
		dl = Stops.Dictlist()

		dl['a'] = 1

		self.assertListEqual([1], dl['a'])
		self.assertEqual(1, len(dl))

		# append test
		dl = Stops.Dictlist()

		dl['a'] = 1
		dl['a'] = 2

		self.assertListEqual([1, 2], dl['a'])
		self.assertEqual(1, len(dl))

		# complex test
		dl = Stops.Dictlist()

		dl['a'] = 1
		dl['b'] = 1
		dl['a'] = 2
		dl['b'] = 3

		self.assertListEqual([1, 2], dl['a'])
		self.assertListEqual([1, 3], dl['b'])
		self.assertEqual(2, len(dl))

	def test_insert(self):
		stops = {'': [
			# main stops
				['U4716Z1', 'Station A', 0, 14.25475],
				['U4717Z2', 'Station B', 1, 14.25999],
				['U4715Z2', 'Station C', 2, 14.26568]
			], 'U4715Z2': [
			# first descendant
				['U4714Z2', 'Stop C.1', 3, 14.28848],
				['U4713Z2', 'Stop C.2', 4, 14.30138]
			], 'U4717Z2': [
			# first descendant
				['U4712Z2', 'Stop B.1', 5, 14.33695]
			], 'U4714Z2': [
			# second descendant
				['U4728Z2', 'Sub Stop C.1.1', 6, 14.38971]
			]
		}

		tests.lib_tests.drop_all_tables()
		database_connection = Database('vehicle_positions_test_database')

		Stops.insert(database_connection, stops, stops[''],'NULL', '')

		result = database_connection.execute_fetchall('SELECT * FROM stops ORDER BY lat')

		# id stop equal parent id of different stop
		self.assertEqual(result[2][0], result[3][2])
		self.assertEqual(result[3][0], result[6][2])



if __name__ == '__main__':
	unittest.main()
