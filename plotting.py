#!/usr/bin/env python3
from datetime import timedelta

import mysql.connector
import matplotlib.pyplot as plt
import numpy as np

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
			ON trip_coordinates.id_trip = inn.id_trip and trip_coordinates.shape_traveled between inn.shape_dist_traveled and inn.lead_stop_shape_dist_traveled 
			order by id_stop, lead_stop, shifted_shape_trav"""
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
			else:
				arrivals.add((row[3].seconds, row[5], row[9].seconds - row[3].seconds))
			shape.append(row[7])
			times_coo.append(row[6].time().hour * 3600 + row[6].time().minute * 60 + row[6].time().second + 3600 - row[3].seconds - row[8])
			times_dep.append(row[3].seconds)

	# This import registers the 3D projection, but is otherwise unused.
	from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import

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

	ax.scatter(times_dep, shape, times_coo)
	ax.scatter(arr_t_d, arr_shape, arr_t_c, c='r')

	ax.set_ylabel('shape dt')
	ax.set_zlabel('time coo')
	ax.set_xlabel('time day')

	plt.title("From " + e[0].split()[0] + " to " + e[0].split()[1] + ", occurrences " + str(e[1]))
	plt.show()

