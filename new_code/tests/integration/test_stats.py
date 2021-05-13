import unittest
from datetime import timedelta, datetime
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from database import Database
from file_system import File_system
import tests.lib_tests

class TestStats(unittest.TestCase):

	def test_trips_len(self):
		database_connection = Database("vehicle_positions_database")

		trips_distances = np.array(database_connection.execute_fetchall("""
			SELECT max(shape_dist_traveled) FROM vehicle_positions_database.rides
			GROUP BY id_trip"""))

		self.assertAlmostEqual(trips_distances.mean(), 17905, 0)
		self.assertAlmostEqual(trips_distances.std(), 13716, 0)

		plt.hist(trips_distances, 20, density=False, width=2000)
		plt.xlabel('délka trasy spoje [m]')
		plt.ylabel('počet spojů')
		# plt.savefig('trips_len.pdf')
		plt.show()

	def test_trips_stops(self):
		database_connection = Database("vehicle_positions_database")

		trips_stops = np.array(database_connection.execute_fetchall("""
			SELECT id_trip, count(shape_dist_traveled) FROM vehicle_positions_database.rides
			GROUP BY id_trip"""))

		self.assertAlmostEqual(trips_stops[:,1].mean(), 17, 0)
		self.assertAlmostEqual(trips_stops[:,1].std(), 10, 0)
		self.assertEqual(len([e for e in trips_stops[:,1] if e == 2]), 192)
		self.assertEqual(len([e for e in trips_stops[:,1] if e == 48]), 8)

		trip_ids = list(map(int, [e[0] for e in trips_stops if e[1] == 2]))

		trip_rides = database_connection.execute_fetchall(
			"""	SELECT
					trip_no
				FROM trips
				WHERE trips.id_trip IN ({seq})
				GROUP BY trip_no""".format(
					seq=','.join(['%s']*len(trip_ids))
			), trip_ids)

		self.assertEqual(len(trip_rides), 20)


	def test_total_delay(self):
		database_connection = Database("vehicle_positions_statistic_database")

		trips_delays = np.array(database_connection.execute_fetchall("""
			SELECT shape_dist_traveled, delay, sdt from trip_coordinates join 
(SELECT id_trip, max(shape_dist_traveled) as sdt FROM rides group by id_trip) as trip_len
ON trip_len.id_trip = trip_coordinates.id_trip and  trip_coordinates.shape_dist_traveled < trip_len.sdt
order by trip_coordinates.id_trip, trip_coordinates.inserted, trip_coordinates.shape_dist_traveled"""))

		last_delays = []
		bins = [[] for _ in range(14)]
		for i in range(len(trips_delays) - 1):
			if trips_delays[i][0] > trips_delays[i + 1][0] and trips_delays[i][0] + 500 > trips_delays[i][2] :
				last_delays.append((trips_delays[i][0], trips_delays[i][1]))
				bins[int(trips_delays[i][0] // 5000)].append(trips_delays[i][1])


		last_delays.append([trips_delays[-1][0], trips_delays[-1][1]])
		bins[int(trips_delays[-1][0] // 5000)].append(trips_delays[-1][1])

		last_delays = np.array(last_delays)

		self.assertEqual(len(last_delays), 8758)

		self.assertAlmostEqual(last_delays[:,1].mean(), 114, 0)
		self.assertAlmostEqual(last_delays[:, 1].std(), 179, 0)

		print(last_delays[:,1].mean())
		print(last_delays[:, 1].std())


		plt.scatter(last_delays[:,0], last_delays[:,1], s=0.2)
		# plt.figure(figsize=(10, 8))
		# plt.subplot()
		# sorted_map = sorted(map)
		ci = np.array([np.array(b).std() for b in bins])
		y = np.array([np.array(b).mean() for b in bins])
		plt.plot([i * 5000 for i in range(14)], y, color='b')
		plt.fill_between([i * 5000 for i in range(14)], (y - ci), (y + ci), color='gray', alpha=.1)
		plt.xlabel('délka trasy spoje [m]')
		plt.ylabel('zpoždění v konečné stanici [s]')
		plt.savefig('trips_total_delay.pdf')
		plt.show()

