#!/usr/bin/env python3
import sys

sys.path.append('../')
import numpy as np

from database import Database
from two_stops_model import Two_stops_model, Norm_data

database_connection = Database(database="vehicle_positions_database")


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

	if model.model.get_name() == 'Linear':
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

	import matplotlib.pyplot as plt
	import matplotlib.ticker as ticker

	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	# Z = None ## disable draw model
	if Z is not None:
		ax.plot_wireframe(xx2, xx1, Z,alpha=0.6)  # grid model

	ax.scatter(model.norm_data.get_day_times(), model.norm_data.get_shapes(), model.norm_data.get_coor_times(), c='#ff7f0e', alpha=0.3)  # known data

	ax.set_ylabel('ujetá vzdálenost [m ' + u'\u00D7' + ' 1' + u'\u2009' + '000]')
	ax.set_zlabel('uplynulý čas [s ' + u'\u00D7' + ' 100]')
	ax.set_xlabel('denní doba [s ' + u'\u00D7' + ' 10' + u'\u2009' + '000]')

	plt.title(dep_stop_name + ' ' + u'\u2192' + ' ' + lead_stop_name)
	plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x/1e4)))
	plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x / 1e3)))
	plt.gca().zaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x / 1e2)))

	plt.show()
	# plt.savefig(dep_stop + '_to_' + arr_stop + '.pdf')
	plt.close()

	print("From " + str(dep_stop) + " to " + str(arr_stop) + ", samples: " + str(samples))


if __name__ == '__main__':
	dep_stop = None
	arr_stop = None

	if dep_stop == None or arr_stop == None:

		num = get_all_pairs()

		for e in num:
			dep_stop = e[0].split()[0]
			arr_stop = e[0].split()[1]

			model = create_model(dep_stop, arr_stop)
			get_plot(model, '-1', dep_stop, arr_stop)

	else:
		model = create_model(dep_stop, arr_stop)
		get_plot(model, '-1', dep_stop, arr_stop)
