#!/usr/bin/env python3
from datetime import timedelta

import mysql.connector
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

from database import Database

from new_code.two_stops_model import Two_stops_model

database_connection = Database()

def timediff_to_sec(timed):
	return timed.time().hour * 3600 + timed.time().minute * 60 + timed.time().second + 3600

def is_business_day(date):
	day_of_week = date.weekday()
	if 0 <= day_of_week < 5:
		return True
	return False



stop_pairs = database_connection.execute_fetchall(
	"""	select inn.id_trip, inn.id_stop, inn.lead_stop, departure_time, inn.lead_stop_departure_time, 
			(inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled) as diff_shape_trav, 
			trip_coordinates.inserted, 
			(trip_coordinates.shape_dist_traveled - inn.shape_dist_traveled) as shifted_shape_trav, 
			trip_coordinates.delay 
		from (
			SELECT id_trip, id_stop, shape_dist_traveled, departure_time, 
				LEAD(id_stop, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop, 
				LEAD(shape_dist_traveled, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled, 
				LEAD(departure_time, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_departure_time 
			FROM rides) as inn 
			JOIN trip_coordinates 
			ON trip_coordinates.id_trip = inn.id_trip and inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled > 1500 and trip_coordinates.shape_dist_traveled between inn.shape_dist_traveled and inn.lead_stop_shape_dist_traveled 
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

for e in num:
	dep_stop = e[0].split()[0]
	arr_stop = e[0].split()[1]
	result = database_connection.execute_fetchall(
		"""	select inn.id_trip, 
				inn.id_stop, 
				inn.lead_stop, 
				inn.departure_time, 
				inn.lead_stop_arrival_time, 
				(inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled) as diff_shape_trav, 
				trip_coordinates.inserted, 
				(trip_coordinates.shape_dist_traveled - inn.shape_dist_traveled) as shifted_shape_trav, 
				trip_coordinates.delay
			from (
				SELECT id_trip, id_stop, shape_dist_traveled, departure_time,
					LEAD(id_stop, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop, 
					LEAD(shape_dist_traveled, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled, 
					LEAD(arrival_time, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_arrival_time 
				FROM rides) as inn 
				JOIN trip_coordinates 
				ON trip_coordinates.id_trip = inn.id_trip and id_stop = %s and lead_stop = %s and trip_coordinates.shape_dist_traveled between (inn.shape_dist_traveled) and (inn.lead_stop_shape_dist_traveled) 
				order by id_stop, lead_stop, shifted_shape_trav""",
		(dep_stop, arr_stop)
	)

	shape_dist_trv = []
	coor_times_norm = []
	coor_times = []
	ids_trip = []
	arrivals = set()
	distance = result[0][5]
	max_traveled_time = 0


	for row in result:
		# reduce errors
		if (timediff_to_sec(row[6]) - row[3].seconds) < 40000:
			if is_business_day(row[6]):
				if row[3].seconds > row[4].seconds:
					arrivals.add((row[4].seconds, row[5], row[4].seconds - row[3].seconds + 24 * 60 * 60))
					if row[4].seconds - row[3].seconds + 24 * 60 * 60 > max_traveled_time:
						max_traveled_time = row[4].seconds - row[3].seconds + 24 * 60 * 60
				else:
					arrivals.add((row[4].seconds, row[5], row[4].seconds - row[3].seconds))
					if row[4].seconds - row[3].seconds > max_traveled_time:
						max_traveled_time = row[4].seconds - row[3].seconds


				ids_trip.append(row[0])
				shape_dist_trv.append(row[7])
				coor_time_norm = timediff_to_sec(row[6]) - row[3].seconds - row[8]
				if coor_time_norm < - 12 * 60 * 60:
					coor_time_norm += 24 * 60 * 60
				coor_times_norm.append(coor_time_norm)
				coor_times.append(timediff_to_sec(row[6]))
				# print("bd", row[0])
			else:
				# print("weekend", row[0])
				pass


	model = Two_stops_model(arr_stop,
							dep_stop,
							distance,
							max_traveled_time,
							shape_dist_trv,
							coor_times_norm,
							coor_times,
							ids_trip).get_model()

	# makes ready input data for training a model
	# input_data = np.array([shape_dist_trv, coor_times]).transpose()
	# input_data = np.pad(input_data, ((0, 0), (0, 1)), constant_values=1)
	#
	# output_data = np.array(coor_times_norm)
	#
	# X_train, X_test, y_train, y_test = train_test_split(input_data, output_data, test_size = 0.33, random_state = 42)
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

	x = np.linspace(0, max(shape_dist_trv), 30)
	y = np.linspace(min(coor_times), max(coor_times), 30)


	# makes grid for model visualization
	xx1, xx2 = np.meshgrid(x, y)
	grid = np.pad(np.array([xx1.ravel(), xx2.ravel()]).T, ((0, 0), (0, 1)), constant_values=1)
	Z = model.predict_standard(xx1.ravel(), xx2.ravel())

	arr_shape = []
	arr_t_c = []
	arr_t_d = []

	# red dots for arrivals times
	for ea in arrivals:
		arr_t_d.append(ea[0])
		arr_shape.append(ea[1])
		arr_t_c.append(ea[2])

	import matplotlib.pyplot as plt

	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	if Z is not None:
		ax.scatter(xx2,xx1, Z, alpha=0.4)  # grid model
	ax.scatter(coor_times, shape_dist_trv, coor_times_norm)  # known data
	# X_train = X_train.transpose()
	# ax.scatter(X_train[1], X_train[0], y_train)
	ax.scatter(arr_t_d, arr_shape, arr_t_c, c='r')  # arrivals

	ax.set_ylabel('shp dist trv')
	ax.set_zlabel('coor time')
	ax.set_xlabel('day time')

	plt.title("From " + e[0].split()[0] + " to " + e[0].split()[1] + ", occurrences " + str(e[1]) + ", poly degree " )
	plt.show()

