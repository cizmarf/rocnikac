import argparse
import json
import lzma
import os
import pickle
import unittest
from pathlib import Path

import tests.lib_tests
from database import Database
from download_and_process import main
from file_system import File_system


# make sure the production database is filled with static data
class TestData(unittest.TestCase):

	def test_mean_stop_distance(self):
		database_connection = Database("vehicle_positions_database")

		database_connection.cursor.execute("""
		SELECT AVG(data_table.diff_shape_trav) 
		FROM (
			SELECT  
        		Avg(schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled) AS diff_shape_trav
			FROM (
				SELECT id_trip, id_stop, shape_dist_traveled,
					LEAD(id_stop, 1) OVER (
						PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
					LEAD(shape_dist_traveled, 1) OVER (
						PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled
				FROM rides) AS schedule
			WHERE schedule.lead_stop IS NOT NULL -- ignores final stop
			GROUP BY schedule.id_stop, schedule.lead_stop) AS data_table;""", )
		result = database_connection.cursor.fetchall()
		self.assertAlmostEqual(float(result[0][0]), 1349.63849181)

	def test_mean_stop_distance_for_all_rides(self):
		database_connection = Database("vehicle_positions_database")

		database_connection.cursor.execute("""
		SELECT AVG(data_table.diff_shape_trav) 
		FROM (
			SELECT  
        		(schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled) AS diff_shape_trav
			FROM (
				SELECT id_trip, id_stop, shape_dist_traveled,
					LEAD(id_stop, 1) OVER (
						PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
					LEAD(shape_dist_traveled, 1) OVER (
						PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled
				FROM rides) AS schedule
			WHERE schedule.lead_stop IS NOT NULL -- ignores final stop
			) AS data_table;""", )
		result = database_connection.cursor.fetchall()
		self.assertAlmostEqual(float(result[0][0]), 1097.6306)

	def test_median_stop_distance(self):
		database_connection = Database("vehicle_positions_database")

		for result in database_connection.cursor.execute("""
			SET @rowindex := -1;
			SELECT AVG(deriv.diff_shape_trav) AS median
				FROM (
					SELECT 
						@rowindex:=@rowindex + 1 AS rowindex,
						data_table.diff_shape_trav AS diff_shape_trav
					FROM (
						SELECT AVG(schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled) AS diff_shape_trav
						FROM (
							SELECT 
								id_trip, id_stop, shape_dist_traveled,
								LEAD(id_stop, 1) OVER (
									PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
								LEAD(shape_dist_traveled, 1) OVER (
									PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled
							FROM rides
						) AS schedule
						WHERE schedule.lead_stop IS NOT NULL -- ignores final stop
						GROUP BY schedule.id_stop, schedule.lead_stop
					) AS data_table
					ORDER BY data_table.diff_shape_trav
				) AS deriv
				WHERE deriv.rowindex IN (FLOOR(@rowindex / 2), CEIL(@rowindex / 2));""", multi=True):
			if result.statement == 'SET @rowindex := -1':  # skips first query, there is nothing to fetch
				continue
			self.assertAlmostEqual(float(result.fetchall()[0][0]), 942.98485)


	def test_median_stop_distance_for_all_rides(self):
		database_connection = Database("vehicle_positions_database")

		for result in database_connection.cursor.execute("""
			SET @rowindex := -1;
			SELECT AVG(deriv.diff_shape_trav) AS median
				FROM (
					SELECT 
						@rowindex:=@rowindex + 1 AS rowindex,
						data_table.diff_shape_trav AS diff_shape_trav
					FROM (
						SELECT (schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled) AS diff_shape_trav
						FROM (
							SELECT 
								id_trip, id_stop, shape_dist_traveled,
								LEAD(id_stop, 1) OVER (
									PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
								LEAD(shape_dist_traveled, 1) OVER (
									PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled
							FROM rides
						) AS schedule
						WHERE schedule.lead_stop IS NOT NULL -- ignores final stop
					) AS data_table
				) AS deriv
				WHERE deriv.rowindex IN (FLOOR(@rowindex / 2), CEIL(@rowindex / 2));""", multi=True):
			if result.statement == 'SET @rowindex := -1':  # skips first query, there is nothing to fetch
				continue
			self.assertAlmostEqual(float(result.fetchall()[0][0]), 718.0)


class TestDatabaseClass(unittest.TestCase):
	# def test_something(self):
	# 	self.assertEqual(True, False)

	# database_connection = Database("vehicle_positions_test_database")

	# def testTest(self):
	# 	self.assertEqual(1,2)

	# def testAExecutionOrder(self):
	# 	self.assertEqual(unittest.defaultTestLoader.getTestCaseNames(FillDatabase), ['testAExecutionOrder', 'testDatabaseConnection', 'testSuccessExecute_transaction_commit_rollback'])

	def testDatabaseConnection(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.cursor.execute('SELECT VERSION()')

	def testSuccessExecute_transaction_commit_rollback(self):
		tests.lib_tests.drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback("INSERT INTO headsigns (headsign) VALUES (%s)", ('test',))
		database_connection.cursor.execute("SELECT headsign FROM headsigns WHERE headsign='test'")
		result = database_connection.cursor.fetchall()
		self.assertEqual(len(result), 1)

	def testFailExecute_transaction_commit_rollback(self):
		tests.lib_tests.drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback("INSERT INTO headsigns (headsign) VALUES (%s)", ('test',))

		try:
			self.assertRaises(IOError, database_connection.execute_transaction_commit_rollback("INSERT INTO headsigns (headsign) VALUES (%s)", ('test',)))
		except Exception:
			pass

	def testFetchall(self):
		tests.lib_tests.drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.cursor.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test1',))
		database_connection.cursor.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test2',))

		result = database_connection.execute_fetchall("SELECT headsign FROM headsigns")

		self.assertEqual(result[0][0], 'test1')
		self.assertEqual(result[1][0], 'test2')

	def testExecute(self):
		tests.lib_tests.drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test1',))
		database_connection.execute("INSERT INTO headsigns (headsign) VALUES (%s)", ('test2',))

		result = database_connection.execute_fetchall("SELECT headsign FROM headsigns")

		self.assertEqual(result[0][0], 'test1')
		self.assertEqual(result[1][0], 'test2')

	def testExecute_many(self):
		tests.lib_tests.drop_all_tables()
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_many("INSERT INTO headsigns (headsign) VALUES (%s)", [('test1',), ('test2',)])

		result = database_connection.execute_fetchall("SELECT headsign FROM headsigns")

		self.assertEqual(result[0][0], 'test1')
		self.assertEqual(result[1][0], 'test2')

	def testExecute_procedure_fetchall(self):
		tests.lib_tests.drop_all_tables()
		args = tests.lib_tests.get_args()
		database_connection = Database("vehicle_positions_test_database")

		from stops import Stops
		from all_vehicle_positions import All_vehicle_positions

		vehicle_positions = All_vehicle_positions()
		vehicle_positions.json_file = json.loads(File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz"))
		vehicle_positions.construct_all_trips(database_connection)
		for vehicle in vehicle_positions.iterate_vehicles():
			if vehicle.trip_id == "421_225_191114":
				vehicle.json_trip = json.loads(File_system.get_file_content(Path("../input_data/421_225_191114.json")))
				vehicle._fill_attributes_from_trip_file()
				vehicle.id_trip = database_connection.execute_fetchall(
					'SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s, %s)',
					vehicle.get_tuple_new_trip(args.static_demo))[0][0]
				Stops.insert_ride_by_trip(database_connection, vehicle)
				database_connection.execute('COMMIT;')
				break

		result = database_connection.execute_procedure_fetchall("get_all_pairs_of_stops", (0, 0, 0))

		# File_system.pickle_object(result, "../output_data/testExecute_procedure_fetchall.obj")

		self.assertEqual(result, File_system.pickle_load_object("../output_data/testExecute_procedure_fetchall.obj"))


if __name__ == '__main__':
	unittest.main()
