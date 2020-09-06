import argparse
import json
import lzma
import os
import pickle
import unittest
from pathlib import Path

from database import Database
from download_and_process import main
from file_system import File_system


class TestDatabaseClass(unittest.TestCase):
	# def test_something(self):
	# 	self.assertEqual(True, False)

	# database_connection = Database("vehicle_positions_test_database")

	parser = argparse.ArgumentParser()
	parser.add_argument("--static_data", default=True, type=bool, help="Fill with static data or dynamic real-time data.")
	parser.add_argument("--static_demo", default=False, type=bool,
						help="Use only if static data in use, time of insert sets now and wait 20 s for next file.")
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--clean_old", default=-1, type=int, help="Deletes all trips inactive for more than set minutes")
	args = parser.parse_args([] if "__file__" not in globals() else None)



	# def testTest(self):
	# 	self.assertEqual(1,2)

	# def testAExecutionOrder(self):
	# 	self.assertEqual(unittest.defaultTestLoader.getTestCaseNames(FillDatabase), ['testAExecutionOrder', 'testDatabaseConnection', 'testSuccessExecute_transaction_commit_rollback'])

	def _drop_all_tables(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

		database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.rides;")
		database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.stops;")
		database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.trip_coordinates;")
		database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.trips;")
		database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.headsigns;")
		database_connection.connection.commit()

		database_connection.cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

		database_connection.close()

	def testDatabaseConnection(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.cursor.execute('SELECT VERSION()')

		database_connection.close()

	def testSuccessExecute_transaction_commit_rollback(self):
		self._drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback("INSERT INTO headsigns (headsign) VALUES (%s)", ('test',))
		database_connection.cursor.execute("SELECT headsign FROM headsigns WHERE headsign='test'")
		result = database_connection.cursor.fetchall()
		self.assertEqual(len(result), 1)

		database_connection.close()

	def testFailExecute_transaction_commit_rollback(self):
		self._drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback("INSERT INTO headsigns (headsign) VALUES (%s)", ('test',))

		try:
			self.assertRaises(IOError, database_connection.execute_transaction_commit_rollback("INSERT INTO headsigns (headsign) VALUES (%s)", ('test',)))
		except Exception:
			pass

		database_connection.close()

	def testFetchall(self):
		self._drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.cursor.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test1',))
		database_connection.cursor.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test2',))

		result = database_connection.execute_fetchall("SELECT headsign FROM headsigns")

		self.assertEqual(result[0][0], 'test1')
		self.assertEqual(result[1][0], 'test2')

		database_connection.close()

	def testExecute(self):
		self._drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test1',))
		database_connection.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test2',))

		result = database_connection.execute_fetchall("SELECT headsign FROM headsigns")

		self.assertEqual(result[0][0], 'test1')
		self.assertEqual(result[1][0], 'test2')

		database_connection.close()

	def testExecute_many(self):
		self._drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_many("INSERT INTO headsigns (headsign) VALUES (%s)", [('test1',), ('test2',)])

		result = database_connection.execute_fetchall("SELECT headsign FROM headsigns")

		self.assertEqual(result[0][0], 'test1')
		self.assertEqual(result[1][0], 'test2')

		database_connection.close()

	def	testExecute_procedure_fetchall(self):
		self._drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		from stops import Stops
		from trip import Trip
		from all_vehicle_positions import All_vehicle_positions

		vehicle_positions = All_vehicle_positions()
		vehicle_positions.json_file = json.loads(File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz"))
		vehicle_positions.construct_all_trips(database_connection)
		for vehicle in vehicle_positions.iterate_vehicles():
			if vehicle.trip_id == "421_225_191114":

				vehicle.json_trip = json.loads(File_system.get_file_content(Path("../input_data/421_225_191114.json")))
				vehicle._fill_attributes_from_trip_file()
				vehicle.id_trip = database_connection.execute_fetchall(
					'SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s)',
					vehicle.get_tuple_new_trip(TestDatabaseClass.args.static_demo))[0][0]
				Stops.insert_ride_by_trip(database_connection, vehicle)
				database_connection.execute('COMMIT;')
				break

		result = database_connection.execute_procedure_fetchall("get_all_pairs_of_stops")

		self.assertEqual(result, File_system.pickle_load_object("../output_data/testExecute_procedure_fetchall.obj"))

		database_connection.close()

	# def testInsertData(self):
	# 	File_system.static_vehicle_positions = Path("/Users/filipcizmar/Documents/rocnikac/raw_data_unittest/")
	#
	# 	# main(FillDatabase.database_connection, FillDatabase.args)
	#
	# 	trips = self.database_connection.execute_fetchall('SELECT * FROM trips')
	# 	print(trips)
	# 	print(len(trips))
	# 	self.assertGreater(len(trips), 1)


if __name__ == '__main__':
	unittest.main()
