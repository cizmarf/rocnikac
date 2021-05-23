import unittest
import numpy as np
import matplotlib.pyplot as plt

from database import Database
from file_system import File_system

###
### The following tests pass only for attached models
### The results may differ if using different input data
###

class TestEstimation(unittest.TestCase):

	@staticmethod
	def compare_delays(old_ride_delay, new_ride_delay):
		old_np = np.array(old_ride_delay)
		new_np = np.array(new_ride_delay)

		print(old_np.std())
		print(new_np.std())

		return old_np.std(), new_np.std()

	@staticmethod
	def compare_estimation(id_trip: int, sdt_dep: int, sdt_arr: int, db_old, db_new):

		old_delay = np.array(db_old.execute_fetchall("""
					SELECT delay, inserted 
					FROM trip_coordinates 
					WHERE id_trip = %s 
						AND shape_dist_traveled BETWEEN %s + 99 AND %s - 99
						AND inserted BETWEEN '2020-02-21 00:00:00' AND '2020-02-21 23:59:59'
					ORDER BY inserted, shape_dist_traveled""",
			(str(id_trip), str(sdt_dep), str(sdt_arr))))

		new_delay = np.array(db_new.execute_fetchall("""
					SELECT delay, inserted 
					FROM trip_coordinates 
					WHERE id_trip = %s 
						AND shape_dist_traveled BETWEEN %s + 99 AND %s - 99
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

		to_return = []

		for i in range(old_delay.shape[0] - 1):
			if old_delay[i + 1, 1].timestamp() < last_inserted.timestamp() + 12 * 60 * 60:
				old_ride_delay.append(old_delay[i + 1, 0])
				new_ride_delay.append(new_delay[i + 1, 0])
			else:

				print('Trip: ' + str(id_trip), ' std between ' + str(sdt_dep) + ' and ' + str(sdt_arr) + ' variance is:')
				to_return.append(TestEstimation.compare_delays(old_ride_delay, new_ride_delay))
				old_ride_delay = [old_delay[i + 1, 0]]
				new_ride_delay = [new_delay[i + 1, 0]]

			last_inserted = old_delay[i + 1, 1]

		print('Trip: ' + str(id_trip), ' std between ' + str(sdt_dep) + ' and ' + str(sdt_arr) + ' variance is:')
		to_return.append(TestEstimation.compare_delays(old_ride_delay, new_ride_delay))
		return to_return

	def test_compare_estimation_534_421(self):
		old_database_connection = Database("vehicle_positions_database")
		new_database_connection = Database("vehicle_positions_fri_delay_estimation_database")

		TestEstimation.compare_estimation(2162, 24647, 31530, old_database_connection, new_database_connection)

		old_delay = np.array(old_database_connection.execute_fetchall("""
					SELECT delay, shape_dist_traveled 
					FROM trip_coordinates 
					WHERE id_trip = %s 
						AND shape_dist_traveled BETWEEN %s + 99 AND %s - 99
						AND inserted BETWEEN '2020-02-21 00:00:00' AND '2020-02-21 23:59:59'
					ORDER BY inserted, shape_dist_traveled""", ('2162', '24647', '31530')))

		new_delay = np.array(new_database_connection.execute_fetchall("""
					SELECT delay, shape_dist_traveled 
					FROM trip_coordinates 
					WHERE id_trip = %s 
						AND shape_dist_traveled BETWEEN %s + 99 AND %s - 99
						AND inserted BETWEEN '2020-02-21 00:00:00' AND '2020-02-21 23:59:59'
					ORDER BY inserted, shape_dist_traveled""", ('2162', '24647', '31530')))

		self.assertLess(new_delay[:,0].std() * 5, old_delay[:,0].std())
		plt.plot(old_delay[:,1], old_delay[:,0], label="lineární odhad", alpha=0.7)
		plt.plot(new_delay[:,1], new_delay[:,0], label="polynomiální odhad")
		plt.xlabel('ujetá vzdálenost [m]')
		plt.ylabel('zpoždění [s]')
		plt.legend(loc='best')
		# plt.savefig('compare_534_421.pdf')
		plt.show()

	def test_compare_all_estimations(self):

		old_database_connection = Database("vehicle_positions_database")
		new_database_connection = Database("vehicle_positions_fri_delay_estimation_database")

		models = File_system.load_all_models()

		stops_variances = []

		for model in models.items():
			print(model[1].dep_stop, model[1].arr_stop)
			all_stop_trips = np.array(new_database_connection.execute_fetchall("""
				SELECT schedule.id_trip, schedule.shape_dist_traveled, schedule.lead_stop_shape_dist_traveled
				FROM (
        SELECT id_trip, id_stop, shape_dist_traveled,
            LEAD(id_stop, 1) OVER (
                PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
            LEAD(shape_dist_traveled, 1) OVER (
                PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled
        FROM rides) AS schedule
				WHERE schedule.id_stop = %s and schedule.lead_stop = %s
				""",
				(model[1].dep_stop, model[1].arr_stop)))

			stop_variance = []

			for row in all_stop_trips:
				trip_variances = np.array(TestEstimation.compare_estimation(row[0], row[1], row[2], old_database_connection, new_database_connection))
				if len(trip_variances.shape) > 0:
					stop_variance.append([trip_variances[:,0].mean(), trip_variances[:,1].mean()])

			stop_variance = np.array(stop_variance)
			stops_variances.append([stop_variance[:,0].mean(), stop_variance[:,1].mean()])

		stops_variances = np.array(stops_variances)
		div = np.divide(stops_variances[:, 0], stops_variances[:, 1], where=stops_variances[:, 1] != 0)
		diff = stops_variances[:, 0] - stops_variances[:, 1]

		print('For ' + str(len([sv for sv in diff if sv >= 1])) + ' segments of trips is the new estimation better.')
		print('For ' + str(len([sv for sv in diff if sv >= 2])) + ' segments of trips is the new estimation significantly better.')
		print('For ' + str(len([sv for sv in diff if sv < 1])) + ' segments of trips is the new estimation worse.')

		self.assertAlmostEqual(diff.mean(), 7, 0)

		self.assertAlmostEqual(stops_variances[:,0].mean(), 19, 0)
		self.assertAlmostEqual(stops_variances[:,1].mean(), 12, 0)

		self.assertAlmostEqual(stops_variances[:,0].std(), 14, 0)
		self.assertAlmostEqual(stops_variances[:,1].std(), 14, 0)

		bins_sv_1 = [0] * 10

		for i in range(len(stops_variances)):
			if stops_variances[i][0] > 90:
				bins_sv_1[9] += 1
			else:
				sv = int((stops_variances[i][0]) // 10)
				bins_sv_1[sv + 1] += 1

		plt.bar([(i) * 10 - 5 for i in range(10)], bins_sv_1, width=8)
		plt.xlabel('Směrodatná odchylka [s]')
		plt.ylabel('Počet dvojic zastávek')
		# plt.savefig('rozptyl_old.pdf')
		plt.show()
		plt.clf()

		bins_sv_2 = [0] * 10

		for i in range(len(stops_variances)):
			if stops_variances[i][1] > 90:
				bins_sv_2[9] += 1
			else:
				sv = int((stops_variances[i][1]) // 10)
				bins_sv_2[sv + 1] += 1

		plt.bar([(i) * 10 - 5 for i in range(10)], bins_sv_2, width=8)
		plt.xlabel('Směrodatná odchylka [s]')
		plt.ylabel('Počet dvojic zastávek')
		# plt.savefig('rozptyl_new.pdf')
		plt.show()
		plt.clf()

		bins_diff = [0] * 8

		for i in range(len(diff)):
			if diff[i] < -20:
				bins_diff[0] += 1
			elif diff[i] > 40:
				bins_diff[7] += 1
			else:
				sv = int((diff[i] + 20) // 10)
				bins_diff[sv + 1] += 1

		plt.bar([(i - 2) * 10 - 5 for i in range(8)], bins_diff, width=8)
		plt.xlabel('Rozdíl rozptylu původního a nového odhadu zpoždění')
		plt.ylabel('Počet dvojic zastávek')
		# plt.savefig('rozptyl_diff.pdf')
		plt.show()
		plt.clf()

		bins_div = [0] * 8

		for i in range(len(div)):
			if div[i] < 0.5:
				bins_div[0] += 1
			elif div[i] < 1:
				bins_div[1] += 1
			elif div[i] > 6:
				bins_div[7] += 1
			else:
				sv = int(div[i])
				bins_div[sv + 1] += 1
		bars = ['< 0.5', '0.5-1', '1-2', '2-3', '3-4', '4-5', '5-6', '6 <']
		# bars = ('A', 'B', 'C', 'D', 'E', 'F', 'E', 'G')
		y_pos = np.arange(len(bars))
		# plt.bar([(i - 2) * 10 - 5 for i in range(8)], bins_div, width=8)
		plt.bar(y_pos, bins_div)

		# use the plt.xticks function to custom labels
		plt.xticks(y_pos, bars, horizontalalignment='center')
		plt.show()
