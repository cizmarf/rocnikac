import unittest
from datetime import timedelta, datetime
from pathlib import Path
import numpy as np

from database import Database
from file_system import File_system
import tests.lib_tests

class TestEstimation(unittest.TestCase):
	worse = 0
	better = 0
	twice_better = 0
	ratio = []

	@staticmethod
	def compare_delays(old_ride_delay, new_ride_delay):
		old_np = np.array(old_ride_delay)
		new_np = np.array(new_ride_delay)

		print(old_np.std())
		print(new_np.std())
		TestEstimation.ratio.append(old_np.std()/new_np.std())
		if old_np.std() < new_np.std():
			TestEstimation.worse += 1
		if old_np.std() > new_np.std():
			TestEstimation.better += 1
		if old_np.std() > new_np.std() * 2:
			TestEstimation.twice_better += 1

	@staticmethod
	def compare_estimation(id_trip: int, sdt_dep: int, sdt_arr: int, db_old, db_new):

		old_delay = np.array(db_old.execute_fetchall("""
					SELECT delay, inserted 
					FROM trip_coordinates 
					WHERE id_trip = %s 
						AND shape_dist_traveled BETWEEN %s AND %s
						AND inserted BETWEEN '2020-02-21 00:00:00' AND '2020-02-21 23:59:59'
					ORDER BY inserted, shape_dist_traveled""",
			(str(id_trip), str(sdt_dep), str(sdt_arr))))

		new_delay = np.array(db_new.execute_fetchall("""
					SELECT delay, inserted 
					FROM trip_coordinates 
					WHERE id_trip = %s 
						AND shape_dist_traveled BETWEEN %s AND %s
						AND inserted BETWEEN '2020-02-21 00:00:00' AND '2020-02-21 23:59:59'
					ORDER BY inserted, shape_dist_traveled""",
			(str(id_trip), str(sdt_dep), str(sdt_arr))))

		assert (old_delay.shape[0] == new_delay.shape[0])
		if len(old_delay.shape) == 1:
			print('For trip: ' + str(id_trip), ' std between ' + str(sdt_dep) + ' and ' + str(sdt_arr) + ' no data has been found.')
			return

		old_ride_delay = [old_delay[0, 0]]
		new_ride_delay = [new_delay[0, 0]]
		last_inserted = old_delay[0, 1]

		for i in range(old_delay.shape[0] - 1):
			if old_delay[i + 1, 1].timestamp() < last_inserted.timestamp() + 12 * 60 * 60:
				old_ride_delay.append(old_delay[i + 1, 0])
				new_ride_delay.append(new_delay[i + 1, 0])
			else:

				print('Trip: ' + str(id_trip), ' std between ' + str(sdt_dep) + ' and ' + str(sdt_arr) + ' variance is:')
				TestEstimation.compare_delays(old_ride_delay, new_ride_delay)
				old_ride_delay = [old_delay[i + 1, 0]]
				new_ride_delay = [new_delay[i + 1, 0]]

			last_inserted = old_delay[i + 1, 1]

		print('Trip: ' + str(id_trip), ' std between ' + str(sdt_dep) + ' and ' + str(sdt_arr) + ' variance is:')
		TestEstimation.compare_delays(old_ride_delay, new_ride_delay)

	def test_compare_estimation_534_421(self):
		TestEstimation.compare_estimation(2162, 24647, 31530, Database("vehicle_positions_database"), Database("vehicle_positions_fri_delay_estimation_database"))

	def test_compare_all_estimations(self):

		old_database_connection = Database("vehicle_positions_database")
		new_database_connection = Database("vehicle_positions_fri_delay_estimation_database")

		models = File_system.load_all_models()

		for model in models.items():
			print(model[1].dep_stop, model[1].arr_stop)
			all_stop_trips = np.array(old_database_connection.execute_fetchall("""
				SELECT id_trip, id_stop, shape_dist_traveled FROM vehicle_positions_database.rides 
				WHERE id_stop = %s or id_stop = %s 
				ORDER BY id_trip, shape_dist_traveled;""",
				(model[1].dep_stop, model[1].arr_stop)))

			last_row = all_stop_trips[0]

			for row in all_stop_trips[1:]:
				if last_row[0] == row[0]:
					TestEstimation.compare_estimation(row[0], last_row[2], row[2], old_database_connection, new_database_connection)
				last_row = row

		print('Finished')
		print('For ' + str(TestEstimation.better) + ' segments of trips is the new estimation better.')
		print('For ' + str(TestEstimation.twice_better) + ' segments of trips is the new estimation significantly better.')
		print('For ' + str(TestEstimation.worse) + ' segments of trips is the new estimation worse.')

