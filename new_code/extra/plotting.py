#!/usr/bin/env python3
import os
from datetime import timedelta
from pathlib import Path
import sys

sys.path.append('../')
# import mysql.connector
# import matplotlib.pyplot as plt
# from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

from database import Database
from file_system import File_system

from two_stops_model import Two_stops_model, Norm_data

database_connection = Database(database="vehicle_positions_statistic_database")


def timediff_to_sec(timed):
	return timed.time().hour * 3600 + timed.time().minute * 60 + timed.time().second + 3600


def is_business_day(date):
	day_of_week = date.weekday()
	if 0 <= day_of_week < 5:
		return True
	return False

def get_all_pairs():
	stop_pairs = database_connection.execute_fetchall(
		"""	select inn.id_trip, inn.id_stop, inn.lead_stop, departure_time, inn.lead_stop_departure_time,
				(inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled) as diff_shape_trav,
				trip_coordinates.inserted,
				(trip_coordinates.shape_dist_traveled - inn.shape_dist_traveled) as shifted_shape_trav,
				trip_coordinates.last_stop_delay
			from (
				SELECT id_trip, id_stop, shape_dist_traveled, departure_time,
					LEAD(id_stop, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
					LEAD(shape_dist_traveled, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled,
					LEAD(departure_time, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_departure_time
				FROM rides) as inn
				JOIN trip_coordinates
				ON trip_coordinates.id_trip = inn.id_trip and inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled > 1000 and trip_coordinates.shape_dist_traveled between inn.shape_dist_traveled and inn.lead_stop_shape_dist_traveled
				-- order by id_stop, lead_stop, shifted_shape_trav"""
	)

	all_pairs = {}

	for row in stop_pairs:
		if str(row[1]) + " " + str(row[2]) in all_pairs:
			all_pairs[str(row[1]) + " " + str(row[2])] += 1
		else:
			all_pairs[str(row[1]) + " " + str(row[2])] = 0

	num = []
	for k, v in all_pairs.items():
		num.append([k, v])

	num.sort(key=lambda x: x[1], reverse=True)

	return num


def create_model(dep_stop, arr_stop):
	result = database_connection.execute_fetchall(
		"""	select inn.id_trip,
				inn.id_stop,
				inn.lead_stop,
				inn.departure_time,
				inn.lead_stop_arrival_time,
				(inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled) as diff_shape_trav,
				trip_coordinates.inserted,
				(trip_coordinates.shape_dist_traveled - inn.shape_dist_traveled) as shifted_shape_trav,
				trip_coordinates.last_stop_delay
			from (
				SELECT id_trip, id_stop, shape_dist_traveled, departure_time,
					LEAD(id_stop, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
					LEAD(shape_dist_traveled, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled,
					LEAD(arrival_time, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_arrival_time
				FROM rides) as inn
				JOIN trip_coordinates
				ON trip_coordinates.id_trip = inn.id_trip and id_stop = %s and lead_stop = %s and trip_coordinates.shape_dist_traveled between (inn.shape_dist_traveled + 99) and (inn.lead_stop_shape_dist_traveled - 99)
				order by id_stop, lead_stop, shifted_shape_trav""",
		(dep_stop, arr_stop)
	)

	model = Two_stops_model(
		result[0][1],
		result[0][2],
		result[0][5],
		"all")

	for sts_row in result:
		if is_business_day(sts_row[6]):
			model.add_row(sts_row[7],  # shape distance traveled from dep stop
						  sts_row[3].seconds,  # departure time
						  sts_row[6],  # day time
						  sts_row[0],  # id trip
						  sts_row[4].seconds,  # arr time
						  sts_row[8])

	if len(model) > 0:
		model.create_model()

	return model

def get_plot(model, samples, dep_stop, arr_stop):

	if model.model.get_name() == 'Hull' or model.model.get_name() == 'Linear':
		return

	dep_stop_name = database_connection.execute_fetchall("""
			SELECT stop_name 
			FROM vehicle_positions_database.stops 
			WHERE id_stop = %s;""",
														 (dep_stop,))[0][0]
	lead_stop_name = database_connection.execute_fetchall("""
				SELECT stop_name 
				FROM vehicle_positions_database.stops 
				WHERE id_stop = %s;""",
														  (arr_stop,))[0][0]

	x = np.linspace(0, model.distance, 30)
	y = np.linspace(model.model.min_day_time, model.model.max_day_time, 30)

	# makes grid for model visualization
	xx1, xx2 = np.meshgrid(x, y)
	grid = np.pad(np.array([xx1.ravel(), xx2.ravel()]).T, ((0, 0), (0, 1)), constant_values=1)
	Z = model.model.predict_standard(xx1.ravel(), xx2.ravel())
	Z = np.reshape(Z, (30, 30))

	# arr_shape = []
	# arr_t_c = []
	# arr_t_d = []

	# red dots for arrivals times
	# for ea in arrivals:
	# 	arr_t_d.append(ea[0])
	# 	arr_shape.append(ea[1])
	# 	arr_t_c.append(ea[2])

	import matplotlib.pyplot as plt
	import matplotlib.ticker as ticker

	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	# Z = None
	if Z is not None:
		ax.plot_wireframe(xx2, xx1, Z,)  # grid model

	# if model.get_name() == "Hull":
	# 	print("is hull")
	# 	lin_arrivals = np.linspace(model.min_day_time, model.max_day_time, 30)
	# 	pred = model.predict_nonstandard(lin_arrivals)
	# 	ax.scatter(lin_arrivals, np.full(30, model.distance), pred)
	# 	points = np.array(model.points_of_concave_hull).transpose()
	# 	ax.scatter(points[0], points[2], points[1])

	ax.scatter(model.norm_data.get_day_times(), model.norm_data.get_shapes(), model.norm_data.get_coor_times(), c='#ff7f0e', alpha=0.3)  # known data
	# X_train = X_train.transpose()
	# ax.scatter(X_train[1], X_train[0], y_train)
	# ax.scatter(arr_t_d, arr_shape, arr_t_c, c='r')  # arrivals

	ax.set_ylabel('distance [m * 100]')
	ax.set_zlabel('travel time [s]')
	ax.set_xlabel('day time [s * 100]')

	plt.title(dep_stop_name + ' ' + u'\u2192' + ' ' + lead_stop_name)
	plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x/1e2)))
	plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x / 1e2)))

	plt.show()
	# plt.savefig(dep_stop + '_to_' + arr_stop + '.pdf')
	plt.close()

	print("From " + str(dep_stop) + " to " + str(arr_stop) + ", samples: " + str(samples))


if __name__ == '__main__':
	dep_stop = 6991  # e[0].split()[0]
	arr_stop = 8607  # e[0].split()[1]

	# num = get_all_pairs()

	# for e in num:
		# dep_stop = e[0].split()[0]
		# arr_stop = e[0].split()[1]

	model = create_model(dep_stop, arr_stop)

	get_plot(model, '-1', dep_stop, arr_stop)

	# shape_dist_trv = []
	# coor_times_norm = []
	# coor_times = []
	# ids_trip = []
	# arrivals = set()
	# distance = result[0][5]
	# max_traveled_time = 0
	#
	# for row in result:
	# 	# reduce errors
	# 	if (timediff_to_sec(row[6]) - row[3].seconds) < 40000:
	# 		if is_business_day(row[6]):
	# 			if row[3].seconds > row[4].seconds:
	# 				arrivals.add((row[4].seconds, row[5], row[4].seconds - row[3].seconds + 24 * 60 * 60))
	# 				if row[4].seconds - row[3].seconds + 24 * 60 * 60 > max_traveled_time:
	# 					max_traveled_time = row[4].seconds - row[3].seconds + 24 * 60 * 60
	# 			else:
	# 				arrivals.add((row[4].seconds, row[5], row[4].seconds - row[3].seconds))
	# 				if row[4].seconds - row[3].seconds > max_traveled_time:
	# 					max_traveled_time = row[4].seconds - row[3].seconds
	#
	# 			ids_trip.append(row[0])
	# 			shape_dist_trv.append(row[7])
	# 			coor_time_norm = timediff_to_sec(row[6]) - row[3].seconds - row[8]
	# 			if coor_time_norm < - 12 * 60 * 60:
	# 				coor_time_norm += 24 * 60 * 60
	# 			coor_times_norm.append(coor_time_norm)
	# 			coor_times.append(timediff_to_sec(row[6]))
	# 		# print("bd", row[0])
	# 		else:
	# 			# print("weekend", row[0])
	# 			pass
	#
	# model = Two_stops_model(arr_stop,
	# 						dep_stop,
	# 						distance,
	# 						max_traveled_time,
	# 						shape_dist_trv,
	# 						coor_times_norm,
	# 						coor_times,
	# 						ids_trip).get_model()
	#
	# # makes ready input data for training a model
	# input_data = np.array([shape_dist_trv, coor_times]).transpose()
	# input_data = np.pad(input_data, ((0, 0), (0, 1)), constant_values=1)
	#
	# output_data = np.array(coor_times_norm)
	#
	# X_train, X_test, y_train, y_test = train_test_split(input_data, output_data, test_size=0.33, random_state=42)
	#
	# best_degree = 3
	# best_error = 9223372036854775807  # maxint
	#
	# for degree in [3, 4, 5, 6, 7, 8]:
	# 	model = make_pipeline(PolynomialFeatures(degree), Ridge())
	# 	model.fit(X_train, y_train)
	# 	pred = model.predict(X_test)
	# 	error = mean_squared_error(y_test, pred)
	# 	if error < best_error:
	# 		best_degree = degree
	# 		best_error = error
	# 	print("Deg:", degree, "Err", error)
	#
	# model = make_pipeline(PolynomialFeatures(best_degree), Ridge())
	# model.fit(input_data, output_data)

	# model = File_system.pickle_load_object(Path('../tests/input_data') / Path("221406_223778_hol.model"))

	# ignore missing linspace

