import unittest
from datetime import timedelta, datetime
from pathlib import Path

from database import Database
from file_system import File_system
import tests.lib_tests

class FillDatabase():
	@staticmethod
	def testInsertData():
		# takes extremely long to time to do
		tests.lib_tests.drop_all_tables("vehicle_positions_database")

		database_connection = Database("vehicle_positions_database")
		args = tests.lib_tests.get_args()

		from download_and_process import main

		main(database_connection, args)

class MyTestCase(unittest.TestCase):

	def testInsertData(self):

		if False:  # takes very long time to fill database
			database_connection = Database("vehicle_positions_test_database")
			# res = database_connection.execute_fetchall('SELECT * FROM vehicle_positions_test_database.trip_coordinates order by last_stop_delay')

			tests.lib_tests.drop_all_tables()
			old_path = File_system.static_vehicle_positions
			File_system.static_vehicle_positions = Path("/Users/filipcizmar/Documents/rocnikac/rocnikac_source/new_code/tests/input_data/raw_vehicle_positions_simple/")

			database_connection = Database("vehicle_positions_test_database")
			args = tests.lib_tests.get_args()

			from download_and_process import main

			main(database_connection, args)

			File_system.static_vehicle_positions = old_path

		database_connection = Database("vehicle_positions_test_database")

		trips = database_connection.execute_fetchall('SELECT count(*) FROM trips')
		trip_coordinates = database_connection.execute_fetchall('SELECT * FROM trip_coordinates where id_trip = 1 ORDER BY shape_dist_traveled')

		self.assertEqual(trips[0][0], 149)
		self.assertEqual(len(trip_coordinates), 3)
		# predicted delay
		self.assertLess(150, trip_coordinates[2][4])
		# last stop delay
		self.assertEqual(309, trip_coordinates[2][6])

	def test_get_all_pairs_of_stops(self):
		database_connection = Database("vehicle_positions_test_database")

		all_trip_coordinates = database_connection.execute_procedure_fetchall('get_all_pairs_of_stops', (0,0, 1500))

		ride_of_trip = database_connection.execute_fetchall('SELECT * FROM rides WHERE id_trip = %s ORDER BY shape_dist_traveled', (all_trip_coordinates[0][0],))

		for i in range(len(ride_of_trip)):
			if ride_of_trip[i][2] == all_trip_coordinates[0][3]:
				self.assertEqual(ride_of_trip[i][1], all_trip_coordinates[0][1])
				self.assertEqual(ride_of_trip[i + 1][1], all_trip_coordinates[0][2])

	def test_insert_new_trip_to_trips_and_coordinates_and_return_id(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback(
			'SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s, %s)',
			('test_id', 'test_headsign', 10, 20, 100, 'no', datetime(1997, 3, 5, 2, 30, 40), 0.01, 0.02))

		headsign = database_connection.execute_fetchall("SELECT * FROM headsigns WHERE headsign = 'test_headsign' LIMIT 1")
		trip = database_connection.execute_fetchall("SELECT * FROM trips WHERE trip_source_id = 'test_id' LIMIT 1")
		trip_coordinates = database_connection.execute_fetchall("SELECT * FROM trip_coordinates WHERE id_trip = " + str(trip[0][0]))

		self.assertEqual('test_headsign', headsign[0][1])

		self.assertEqual(headsign[0][0], trip[0][2])
		self.assertEqual(10, trip[0][3])
		self.assertEqual(100, trip[0][4])
		self.assertEqual(datetime(1997, 3, 5, 2, 30, 40), trip[0][5])
		self.assertEqual('no', trip[0][6])

		self.assertEqual(0.01, float(trip_coordinates[0][1]))
		self.assertEqual(0.02, float(trip_coordinates[0][2]))
		self.assertEqual(datetime(1997, 3, 5, 2, 30, 40), trip_coordinates[0][3])
		self.assertEqual(10, trip_coordinates[0][4])
		self.assertEqual(100, trip_coordinates[0][5])
		self.assertEqual(20, trip_coordinates[0][6])

		database_connection.execute("DELETE FROM trip_coordinates WHERE id_trip = " + str(trip[0][0]))
		database_connection.execute("DELETE FROM trips WHERE id_trip = " + str(trip[0][0]))
		database_connection.execute("DELETE FROM headsigns WHERE id_headsign = " + str(headsign[0][0]))

	def test_cascade_delete(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback(
			'SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s, %s)',
			('test_id', 'test_headsign', 10, 20, 100, 'no', datetime(1997, 3, 5, 2, 30, 40), 0.01, 0.02))

		database_connection.execute("DELETE FROM trips WHERE trip_source_id = 'test_id'")

		headsign = database_connection.execute_fetchall("SELECT * FROM headsigns WHERE headsign = 'test_headsign' LIMIT 1")
		trip = database_connection.execute_fetchall("SELECT * FROM trips WHERE trip_source_id = 'test_id' LIMIT 1")
		trip_coordinates = database_connection.execute_fetchall("SELECT * FROM trip_coordinates WHERE inserted = %s", (datetime(1997, 3, 5, 2, 30, 40),))

		# headsign does not aim to trip but trip aims to headsign
		database_connection.execute("DELETE FROM headsigns WHERE id_headsign = " + str(headsign[0][0]))

		self.assertEqual(1, len(headsign))
		self.assertEqual(0, len(trip))
		self.assertEqual(0, len(trip_coordinates))

if __name__ == '__main__':
	# FillDatabase.testInsertData()
	unittest.main()
