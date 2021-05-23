import glob
import math
import unittest

from database import Database
from file_system import File_system
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


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

class TestGeneratePlots(unittest.TestCase):
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

		plt.figure(figsize=(12, 8))
		plt.subplot()
		plt.bar(names, no_of_stops_in_distances)
		plt.xlabel('Vzdálenost v km')
		plt.ylabel('Počet úseků')
		plt.yscale('log')
		# plt.savefig('stop_distances_result.pdf')
		plt.show()

	def test_histogram_of_found_trips(self):
		with open("../input_data/fill_database_output", "r") as file:
			map = {}
			cur_trips = 0
			file.readline()
			line = file.readline() # skipps first line
			while line != '':
				if 'raw_trips' in line:
					cur_trips += 1
				else:
					if cur_trips in map:
						map[cur_trips] += 1
					else:
						map[cur_trips] = 1
					cur_trips = 0
				line = file.readline()

			plt.figure(figsize=(10, 8))
			plt.subplot()
			sorted_map = [(k, map[k]) for k in sorted(map, key=map.get, reverse=True)]
			plt.bar([k[0] for k in sorted_map], [v[1] for v in sorted_map])

			self.assertEqual(sum([v[1] for v in sorted_map]), 15793)
			plt.xlabel('Počet nových spojů')
			plt.ylabel('Počet souborů')
			plt.yscale('log')
			plt.savefig('new_trips.pdf')
			plt.show()

	def test_histogram_of_all_trips(self):
		sufix = '/*.tar.gz'
		self.files = glob.glob(str(File_system.static_vehicle_positions) + sufix)
		self.files = sorted(self.files)

		map = {}

		for file in self.files:
			content = File_system.get_tar_file_content(file).decode("utf-8")
			count = math.floor(content.count('coordinates') / 10.0) * 10
			if round(count, -1) in map:
				map[round(count, -1)] += 1
			else:
				map[round(count, -1)] = 1

		plt.figure(figsize=(10, 8))
		plt.subplot()
		sorted_map = [(k, map[k]) for k in sorted(map, key=map.get, reverse=True)]
		plt.bar([k[0] for k in sorted_map], [v[1] for v in sorted_map], width=8)
		# plt.title('Počet souborů s polohy vozidel s počtem spojů. Agregováno po desítkách.')
		plt.xlabel('Počet vozidel')
		plt.ylabel('Počet souborů')
		plt.yscale('log')
		plt.savefig('all_trips.pdf')
		plt.show()

	def test_size_of_all_samples(self):
		database_connection = Database('vehicle_positions_database')

		# demo app needs aprox 30 secs to fetch
		# in production it may takes longer time to fetch all data
		database_connection.execute('SET GLOBAL connect_timeout=600')
		database_connection.execute('SET GLOBAL wait_timeout=600')
		database_connection.execute('SET GLOBAL interactive_timeout=600')

		stop_to_stop_data = database_connection.execute_procedure_fetchall(
			'get_all_pairs_of_stops', (0, 0, 1500))

		File_system.pickle_object(stop_to_stop_data, str(File_system.cwd / Path('tests/output_data/') / Path('all_samples')))

		self.assertEqual(9914112, Path(str(File_system.cwd / Path('tests/output_data/') / Path('all_samples'))).stat().st_size)

	def test_built_models(self):
		class model_stops_log:
			stop_dep = 0
			stop_arr = 0
			rmse_bss = None
			samples_bss = 0
			reduced_samples_bss = 0
			enough_bss = None
			type_bss = None
			degree_bss = None
			rmse_hol = None
			samples_hol = 0
			reduced_samples_hol = 0
			enough_hol = None
			type_hol = None
			degree_hol = None
			time = None

		with open("../input_data/build_models_output", "r") as file:
			models_log = []
			model_log = None
			line = file.readline()
			while line != '':
				if 'Building models between' in line:
					model_log = model_stops_log()
					model_log.stop_arr = int(line.split()[3])
					model_log.stop_dep = int(line.split()[5])
				if 'bss:' in line:
					model_log.samples_bss = int(line.split()[1][:len(line.split()[1]) - 1])
					model_log.samples_hol = int(line.split()[3])
					if model_log.samples_bss == 0 or model_log.samples_hol == 0:
						if model_log.samples_bss != 0:
							line = file.readline()
							model_log.reduced_samples_bss = int(line.split()[3])
							line = file.readline()
							if 'not enough' in line:
								model_log.enough_bss = False
							elif 'degree' in line:
								model_log.enough_bss = True
								model_log.degree_bss = int(line.split()[1])
								line = file.readline()
								model_log.rmse_bss = float(line.split()[5])
							else:
								print('should not occur')
						if model_log.samples_hol != 0:
							line = file.readline()
							model_log.reduced_samples_hol = int(line.split()[3])
							line = file.readline()
							if 'not enough' in line:
								model_log.enough_hol = False
							elif 'degree' in line:
								model_log.enough_hol = True
								model_log.degree_hol = int(line.split()[1])
								line = file.readline()
								model_log.rmse_hol = float(line.split()[5])
							else:
								print('should not occur')
					else:
						line = file.readline()
						model_log.reduced_samples_bss = int(line.split()[3])
						line = file.readline()
						if 'not enough' in line:
							model_log.enough_bss = False
						elif 'degree' in line:
							model_log.enough_bss = True
							model_log.degree_bss = int(line.split()[1])
							line = file.readline()
							model_log.rmse_bss = float(line.split()[5])
						else:
							print('should not occur')

						line = file.readline()
						model_log.reduced_samples_hol = int(line.split()[3])
						line = file.readline()
						if 'not enough' in line:
							model_log.enough_hol = False
						elif 'degree' in line:
							model_log.enough_hol = True
							model_log.degree_hol = int(line.split()[1])
							line = file.readline()
							model_log.rmse_hol = float(line.split()[5])
						else:
							print('should not occur (rmse)')

					line = file.readline()
					if line.split()[0] != '_':
						model_log.type_bss = line.split()[0]

					if line.split()[1] != '_':
						model_log.type_hol = line.split()[1]

					if 'seconds' in line:
						model_log.time = float(line.split()[5])
						models_log.append(model_log)
					else:
						print('should not occur (time)')
				line = file.readline()

			reduces = [log.reduced_samples_bss / log.samples_bss for log in models_log if log.samples_bss != 0]
			reduces.extend([log.reduced_samples_hol / log.samples_hol for log in models_log if log.samples_hol != 0])
			reduces = np.array(reduces)
			print(reduces.max())
			print(np.mean(reduces))

			degrees = [log.degree_bss for log in models_log if log.type_bss == 'Poly']
			degrees.extend([log.degree_hol for log in models_log if log.type_hol == 'Poly'])
			degrees = np.array(degrees)

			rmses_bss = [log.rmse_bss for log in models_log if log.type_bss == 'Poly']

			print(rmses_bss)
			rmse_bss = np.array(rmses_bss)
			rmses_hol = [log.rmse_hol for log in models_log if log.type_hol == 'Poly']
			rmse_hol = np.array(rmses_hol)
			# times_elapsed = np.array(times_elapsed)
			# print(pairs)
			print(len(rmse_bss))
			print(np.mean(rmse_bss))
			print(rmse_bss.max())
			print(len(rmse_hol))
			print(np.mean(rmse_hol))
			print(rmse_hol.max())
			#
			# print(len([None for log in models_log if log.type_bss == 'Linear' and log.rmse_bss != None]))
			# # print(np.mean(times_elapsed))
			# # print(times_elapsed.max())
			#
			# # mu = np.mean(rmse_bss)
			# # sigma = np.std(rmse_bss)
			plt.hist(np.append(rmse_bss, rmse_hol), 40, density=False)
			plt.xlabel('RMSE [s]')
			plt.ylabel('Počet modelů')

			# plt.plot(bins)#, 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(- (bins - mu) ** 2 / (2 * sigma ** 2)), linewidth=2, color='r')
			plt.savefig('rmse.pdf')
			plt.show()

			# plt.figure(figsize=(10, 8))
			# plt.subplot()
			# sorted_map = [(k, map[k]) for k in sorted(map, key=map.get, reverse=True)]
			# plt.bar([k[0] for k in sorted_map], [v[1] for v in sorted_map])
			#
			# self.assertEqual(sum([v[1] for v in sorted_map]), 15793)
			# plt.title('Počet souborů s polohy vozidel s počtem nově objevených spojů.')
			# plt.xlabel('Počet nových spojů')
			# plt.ylabel('Počet souborů')
			# plt.yscale('log')
			# # plt.savefig('books_read.pdf')
			# plt.show()

	def test_get_linear_vs_poly(self):

		## y should be polynomial function
		## for this example tangent looks better and it is easier to visualize
		## it is described as a polynomial function to prevent confusing the reader
		x = np.linspace(-1, 1, 100)
		y = np.tan(x)

		x = (x + 1) * 5
		y = (y + np.tan(1)) * ( 720 / (np.tan(1) * 2))

		x1 = np.linspace(-0.9, -0.7, 100)
		y1 = np.tan(x1)

		x1 = (x1 + 1) * 5
		y1 = (y1 + np.tan(1)) * (720 / (np.tan(1) * 2))

		x2 = np.linspace(-0.1, 0.1, 100)
		y2 = np.tan(x2)

		x2 = (x2 + 1) * 5
		y2 = (y2 + np.tan(1)) * (720 / (np.tan(1) * 2))

		plt.plot([0, 10], [0, 720], label="lineární profil jízdy")
		plt.plot(x, y, label="polynomiální profil jízdy")

		plt.fill([0, 0, x2[-1], x2[-1], x2[0], x2[0]], [y2[0], y2[-1], y2[-1], 0, 0, y2[0]], 'C3', alpha=0.2, label='4,5.' + u'\u2013' + '5,5. km, 46 s')
		plt.fill([0, 0, x1[-1], x1[-1], x1[0], x1[0]], [y1[0], y1[-1], y1[-1], 0, 0, y1[0]], 'C2', alpha=0.2, label='0,5.' + u'\u2013' + '1,5. km, 97 s')

		print(y1[-1] - y1[0])
		print(y2[-1] - y2[0])

		# plt.plot([0, x1[-1]], [120,120])
		plt.xlabel('ujetá vzdálenost [km]')
		plt.ylabel('uplynulý čas jízdy [s]')
		plt.legend(loc='best')
		# plt.savefig('lin_vs_poly.pdf')
		plt.show()

	def test_get_concave_hull(self):

		plt.plot([0, 8, 8.5, 10], np.array([0, 300, 656, 720]) + 20, label='zdržení v prvním kritickém bodě')
		plt.plot([0, 1.5, 2, 10], np.array([0, 64, 420, 720]) + 40, label='zdržení v druhém kritickém bodě')
		plt.plot([0, 10], np.array([0, 375]) + 0, label='průjezd trasy bez zdržení')
		plt.plot([0, 1.5, 2, 8, 8.5, 10], np.array([0, 64, 420, 645,  1001, 1057]) + 60, label='zdržení v obou kritických bodech')
		print( np.concatenate((np.array([0, 300, 656, 720]) + 20, np.array([720, 420, 64, 0]) + 40)))
		plt.fill([0, 8, 8.5, 10, 10, 2, 1.5, 0], np.concatenate((np.array([0, 300, 656, 720]) + 20, np.array([720, 420, 64, 0]) + 40)), 'C1', alpha=0.2, label='prostor s neměnícím se odhadem zpoždění')

		plt.annotate('1. kritický bod (x)', xy=(1.5, 0))
		plt.annotate('2. kritický bod (y)', xy=(7.7, 0))  # should be 8

		plt.xlabel('ujetá vzdálenost [km]')
		plt.ylabel('uplynulý čas jízdy [s]')
		plt.legend(loc='best')
		# plt.savefig('concave_hull.pdf')
		plt.show()

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
			SELECT shape_dist_traveled, delay, sdt FROM trip_coordinates 
				JOIN (
					SELECT id_trip, max(shape_dist_traveled) AS sdt 
					FROM rides 
					GROUP BY id_trip
				) AS trip_len
				ON trip_len.id_trip = trip_coordinates.id_trip AND trip_coordinates.shape_dist_traveled < trip_len.sdt
			ORDER BY trip_coordinates.id_trip, trip_coordinates.inserted, trip_coordinates.shape_dist_traveled"""))

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
		# plt.savefig('trips_total_delay.pdf')
		plt.show()


if __name__ == '__main__':
	unittest.main()
