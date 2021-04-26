import unittest
from datetime import timedelta, datetime
from pathlib import Path
import numpy as np

from database import Database
from file_system import File_system
import tests.lib_tests

class TestEstimation(unittest.TestCase):

	@staticmethod
	def compare_delays(old: list, new: list):
		old_np = np.array(old)
		new_np = np.array(new)

		print(old_np.std())
		print(new_np.std())

	def test_compare_estimation_534_421(self):
		old_database_connection = Database("vehicle_positions_database")

		old_delay = np.array(old_database_connection.execute_fetchall("""
			SELECT delay, inserted 
			FROM trip_coordinates 
			WHERE id_trip = %s AND shape_dist_traveled BETWEEN %s AND %s
			ORDER BY inserted, shape_dist_traveled""",
		('2162', '24647', '31530')))

		new_database_connection = Database("vehicle_positions_delay_estimation_database")

		new_delay = np.array(new_database_connection.execute_fetchall("""
			SELECT delay, inserted 
			FROM trip_coordinates 
			WHERE id_trip = %s AND shape_dist_traveled BETWEEN %s AND %s
			ORDER BY inserted, shape_dist_traveled""",
		('2162', '24647', '31530')))

		assert (old_delay.shape[0] == new_delay.shape[0])

		old_ride_delay = [old_delay[0,0]]
		new_ride_delay = [new_delay[0, 0]]
		last_inserted = old_delay[0,1]

		for i in range(old_delay.shape[0]):
			if old_delay[i,1].timestamp() < last_inserted.timestamp() + 12 * 60 * 60:
				old_ride_delay.append(old_delay[i,0])
				new_ride_delay.append(new_delay[i, 0])
			else:
				TestEstimation.compare_delays(old_ride_delay, new_ride_delay)
				old_ride_delay = [old_delay[i, 0]]
				new_ride_delay = [new_delay[i, 0]]
			last_inserted = old_delay[i, 1]


		TestEstimation.compare_delays(old_ride_delay, new_ride_delay)




	def test_insert_new_trip_to_trips_and_coordinates_and_return_id(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback("""
			SELECT insert_new_trip_to_trips_and_coordinates_and_return_id
			(%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
			('test_id', 'test_headsign', 10, 20, 100, 'no', datetime(1997, 3, 5, 2, 30, 40), 0.01, 0.02))

		headsign = database_connection.execute_fetchall("""
			SELECT * 
			FROM headsigns 
			WHERE headsign = 'test_headsign' 
			LIMIT 1""")
		trip = database_connection.execute_fetchall("""
			SELECT * 
			FROM trips 
			WHERE trip_source_id = 'test_id' 
			LIMIT 1""")
		trip_coordinates = database_connection.execute_fetchall("""
			SELECT * 
			FROM trip_coordinates 
			WHERE id_trip = """ + str(trip[0][0]))

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

		database_connection.execute("""
			DELETE FROM trip_coordinates 
			WHERE id_trip = """ + str(trip[0][0]))
		database_connection.execute("""
			DELETE FROM trips 
			WHERE id_trip = """ + str(trip[0][0]))
		database_connection.execute("""
			DELETE FROM headsigns 
			WHERE id_headsign = """ + str(headsign[0][0]))

	def test_cascade_delete(self):
		database_connection = Database("vehicle_positions_test_database")

		database_connection.execute_transaction_commit_rollback("""
			SELECT insert_new_trip_to_trips_and_coordinates_and_return_id
			(%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
			('test_id', 'test_headsign', 10, 20, 100, 'no', datetime(1997, 3, 5, 2, 30, 40), 0.01, 0.02))

		database_connection.execute("""
			DELETE FROM trips 
			WHERE trip_source_id = 'test_id'""")

		headsign = database_connection.execute_fetchall("""
			SELECT * 
			FROM headsigns 
			WHERE headsign = 'test_headsign' 
			LIMIT 1""")
		trip = database_connection.execute_fetchall("""
			SELECT * 
			FROM trips 
			WHERE trip_source_id = 'test_id' 
			LIMIT 1""")
		trip_coordinates = database_connection.execute_fetchall("""
			SELECT * 
			FROM trip_coordinates 
			WHERE inserted = %s""",
		(datetime(1997, 3, 5, 2, 30, 40),))

		# headsign does not aim to trip but trip aims to headsign
		database_connection.execute("""
			DELETE FROM headsigns 
			WHERE id_headsign = """ + str(headsign[0][0]))

		self.assertEqual(1, len(headsign))
		self.assertEqual(0, len(trip))
		self.assertEqual(0, len(trip_coordinates))

if __name__ == '__main__':
	FillDatabase.testInsertData()
	# unittest.main()
