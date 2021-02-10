import argparse
import json
import lzma
import os
import pickle
import unittest
from pathlib import Path
import matplotlib.pyplot as plt
import tests.lib_tests
from database import Database
from download_and_process import main
from file_system import File_system


# make sure the production database is filled with static data for Thu 20/02/2020
class TestData(unittest.TestCase):

	def test_mean_stop_distance(self):
		database_connection = Database("vehicle_positions_statistic_database")

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
		self.assertAlmostEqual(float(result[0][0]), 1343.37758671)

	def test_mean_stop_distance_for_all_rides(self):
		database_connection = Database("vehicle_positions_statistic_database")

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
		self.assertAlmostEqual(float(result[0][0]), 1111.3123)

	def test_median_stop_distance(self):
		database_connection = Database("vehicle_positions_statistic_database")

		result = database_connection.cursor.execute("""
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
				WHERE deriv.rowindex IN (FLOOR(@rowindex / 2), CEIL(@rowindex / 2));""", multi=True)

		# bug in python 3.7
		self.assertAlmostEqual(float(list(result)[1].fetchall()[0][0]), 943.0)

	def test_median_stop_distance_for_all_rides(self):
		database_connection = Database("vehicle_positions_statistic_database")

		result = database_connection.cursor.execute("""
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
				WHERE deriv.rowindex IN (FLOOR(@rowindex / 2), CEIL(@rowindex / 2));""", multi=True)

		self.assertAlmostEqual(float(list(result)[1].fetchall()[0][0]), 740.0)

	def test_histogram_of_stop_distance_for_all_rides(self):
		database_connection = Database("vehicle_positions_statistic_database")

		database_connection.cursor.execute("""			
		SELECT (schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled) AS diff_shape_trav
		FROM (
			SELECT id_trip, id_stop, shape_dist_traveled,
			LEAD(id_stop, 1) OVER (
				PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
			LEAD(shape_dist_traveled, 1) OVER (
				PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled
			FROM rides
		) AS schedule
		WHERE schedule.lead_stop IS NOT NULL -- ignores final stop
		ORDER BY diff_shape_trav""")

		result = database_connection.cursor.fetchall()
		no_of_stops_in_distances = []
		current_count = 0
		index = 0

		step = 2000
		current_min_border = 0
		top_border = 36000

		assert (top_border % step == 0)

		for i in range(top_border // step + 1):
			while index < len(result) and current_min_border <= result[index][0] < current_min_border + step:
				current_count += 1
				index += 1
			if index < len(result) and i == top_border // step and result[index][0] >= top_border:
				current_count += len(result[index:])
			no_of_stops_in_distances.append(current_count)
			current_min_border += step
			current_count = 0

		self.assertEqual(no_of_stops_in_distances[0], 133575)
		self.assertEqual(no_of_stops_in_distances[8], 173)

		names = [str(int(i * step // 1000)) + '-' + str(int((i + 1) * step // 1000)) for i in range(top_border // step)]
		names.append(str(top_border // 1000) + ' <')
		print(names)
		print(no_of_stops_in_distances)

		plt.figure(figsize=(10, 8))
		plt.subplot()
		plt.bar(names, no_of_stops_in_distances)
		plt.title('Počet úseků mezi bezprostředně následujícími zastávkami a vzdálenost mezi nimi. \n Každý průjezd úsekem je započítán zvlášť.')
		plt.xlabel('Vzdálenost v km')
		plt.ylabel('Počet úseků')
		plt.yscale('log')
		plt.show()

	def test_mean_stop_travel_time(self):
		database_connection = Database("vehicle_positions_statistic_database")

		database_connection.cursor.execute("""
		SELECT AVG(data_table.diff_time) 
		FROM (
		SELECT (schedule.lead_stop_arrival_time - schedule.departure_time) AS diff_time
			FROM (
				SELECT id_trip, id_stop, departure_time,
				LEAD(id_stop, 1) OVER (
					PARTITION BY id_trip ORDER BY arrival_time) lead_stop,
				LEAD(arrival_time, 1) OVER (
					PARTITION BY id_trip ORDER BY arrival_time) lead_stop_arrival_time
			FROM rides
            ) AS schedule
			WHERE schedule.lead_stop IS NOT NULL -- ignores final stop
			-- GROUP BY schedule.id_stop, schedule.lead_stop
            ORDER BY schedule.id_stop, schedule.lead_stop
            ) AS data_table""", )
		result = database_connection.cursor.fetchall()
		self.assertAlmostEqual(float(result[0][0]), 331.9068)

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
