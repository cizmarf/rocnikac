#!/usr/bin/env python3
from datetime import timedelta

import mysql.connector
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

from common_functions import SQL_queries

connection_db = mysql.connector.connect(
			host="localhost",
			database="vehicles_info",
			user="vehicles_access",
			passwd="my_password",
			autocommit=True
		)
cursor_prepared_db = connection_db.cursor(prepared=True)
cursor_db = connection_db.cursor()


result = SQL_queries.sql_get_result(
	cursor_db,
	"""	select inn.id_trip, inn.id_stop, inn.lead_stop, departure_time, inn.lead_stop_departure_time, 
			(inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled) as diff_shape_trav, 
			trip_coordinates.time, 
			(trip_coordinates.shape_traveled - inn.shape_dist_traveled) as shifted_shape_trav, 
			trip_coordinates.delay 
		from (
			SELECT id_trip, id_stop, shape_dist_traveled, departure_time, 
				LEAD(id_stop, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop, 
				LEAD(shape_dist_traveled, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled, 
				LEAD(departure_time, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_departure_time 
			FROM rides) as inn 
			JOIN trip_coordinates 
			ON trip_coordinates.id_trip = inn.id_trip and inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled > 1500 and trip_coordinates.shape_traveled between inn.shape_dist_traveled and inn.lead_stop_shape_dist_traveled 
			-- order by id_stop, lead_stop, shifted_shape_trav"""
)

all_pairs = {}

for row in result:
	if str(row[1]) + " " + str(row[2]) in all_pairs:
		all_pairs[str(row[1]) + " " + str(row[2])] += 1
	else:
		all_pairs[str(row[1]) + " " + str(row[2])] = 0

num = []
for k, v in all_pairs.items():
	num.append([k, v])

num.sort(key=lambda x: x[1], reverse=True)

for e in num:
	result = SQL_queries.sql_get_result(
		cursor_db,
		"""	select inn.id_trip, inn.id_stop, inn.lead_stop, inn.departure_time, inn.lead_stop_arrival_time, 
				(inn.lead_stop_shape_dist_traveled - inn.shape_dist_traveled) as diff_shape_trav, 
				trip_coordinates.time, 
				(trip_coordinates.shape_traveled - inn.shape_dist_traveled) as shifted_shape_trav, 
				trip_coordinates.delay,
				inn.lead_stop_arrival_time
			from (
				SELECT id_trip, id_stop, shape_dist_traveled, departure_time,
					LEAD(id_stop, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop, 
					LEAD(shape_dist_traveled, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled, 
					LEAD(arrival_time, 1) OVER (PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_arrival_time 
				FROM rides) as inn 
				JOIN trip_coordinates 
				ON trip_coordinates.id_trip = inn.id_trip and id_stop = %s and lead_stop = %s and trip_coordinates.shape_traveled between (inn.shape_dist_traveled + 51) and (inn.lead_stop_shape_dist_traveled - 51) 
				order by id_stop, lead_stop, shifted_shape_trav""",
		(e[0].split()[0], e[0].split()[1])
	)

	shape = []
	times_coo = []
	times_dep = []
	arrivals = set()


	for row in result:
		if (row[6].time().hour * 3600 + row[6].time().minute * 60 + row[6].time().second + 3600 - row[3].seconds) < 40000:
			if row[3].seconds > row[9].seconds:
				arrivals.add((row[3].seconds, row[5], row[9].seconds - row[3].seconds + 24 * 60 * 60))
				# arrivals.add((row[6].time().hour * 3600 + row[6].time().minute * 60 + row[6].time().second + 3600, row[5], row[9].seconds - row[3].seconds + 24 * 60 * 60))
			else:
				arrivals.add((row[3].seconds, row[5], row[9].seconds - row[3].seconds))
				# arrivals.add((row[6].time().hour * 3600 + row[6].time().minute * 60 + row[6].time().second + 3600, row[5], row[9].seconds - row[3].seconds))
			shape.append(row[7])
			times_coo.append(row[6].time().hour * 3600 + row[6].time().minute * 60 + row[6].time().second + 3600 - row[3].seconds - row[8])
			times_dep.append(row[3].seconds)
			# times_dep.append(row[6].time().hour * 3600 + row[6].time().minute * 60 + row[6].time().second + 3600)
	# This import registers the 3D projection, but is otherwise unused.
	from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import

	input_data = np.array([shape, times_dep]).transpose()
	input_data = np.pad(input_data, ((0, 0), (0, 1)), constant_values=1)

	output_data = np.array(times_coo)

	X_train, X_test, y_train, y_test = train_test_split(input_data, output_data, test_size = 0.33, random_state = 42)

	best_degree = 3
	best_error = 9223372036854775807

	for degree in [3, 4, 5, 6, 7, 8]:
		model = make_pipeline(PolynomialFeatures(degree), Ridge())
		model.fit(X_train, y_train)
		pred = model.predict(X_test)
		error = mean_squared_error(y_test, pred)
		if error < best_error:
			best_degree = degree
			best_error = error
		print("Deg:", degree, "Err", error)

	model = make_pipeline(PolynomialFeatures(best_degree), Ridge())
	model.fit(input_data, output_data)

	x = np.linspace(0, max(shape), 30)
	y = np.linspace(min(times_dep), max(times_dep), 30)

	xx1, xx2 = np.meshgrid(x, y)
	# print 'meshgrid:', xx1, xx2

	# CLASSIFIER PREDICT
	grid = np.pad(np.array([xx1.ravel(), xx2.ravel()]).T, ((0, 0), (0, 1)), constant_values=1)
	Z = model.predict(grid)
	# Z = Z.reshape(xx1.shape)


	arr_shape = []
	arr_t_c = []
	arr_t_d = []

	for ea in arrivals:
		arr_t_d.append(ea[0])
		arr_shape.append(ea[1])
		arr_t_c.append(ea[2])

	import matplotlib.pyplot as plt

	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	ax.scatter(xx2,xx1, Z, alpha=0.4)
	ax.scatter(times_dep, shape, times_coo)
	# X_train = X_train.transpose()
	# ax.scatter(X_train[1], X_train[0], y_train)
	ax.scatter(arr_t_d, arr_shape, arr_t_c, c='r')

	ax.set_ylabel('shape dt')
	ax.set_zlabel('time coo')
	ax.set_xlabel('time day')

	plt.title("From " + e[0].split()[0] + " to " + e[0].split()[1] + ", occurrences " + str(e[1]) + "degree" + str(best_degree))
	plt.show()

