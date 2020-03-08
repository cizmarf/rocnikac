import argparse
import time

import mysql.connector

from new_code.all_vehicle_positions import All_vehicle_positions, Static_all_vehicle_positions
from new_code.database import Database
from new_code.stops import Stops
from new_code.trip import Trip

parser = argparse.ArgumentParser()
parser.add_argument("--static_data", default=False, type=bool, help="Fill with static data or dynamic real-time data.")
parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
args = parser.parse_args([] if "__file__" not in globals() else None)

database_connection = Database()
# trips_black_list = set()

if args.static_data:
	static_all_vehicle_positions = Static_all_vehicle_positions()
	static_iterator = static_all_vehicle_positions.static_get_all_vehicle_positions_json()

while True:
	req_start = time.time()

	"""
		Update positions file with priority
	"""
	# print("nacitam pozice")

	all_vehicle_positions = All_vehicle_positions()

	if args.static_data:
		try:
			all_vehicle_positions.json_file = next(static_iterator)
		except StopIteration:
			break
	else:

		all_vehicle_positions.get_all_vehicle_positions_json()

	all_vehicle_positions.construct_all_trips()

	# update real-time data file as soon as possible
	all_vehicle_positions.update_geojson_file()

	for vehicle in all_vehicle_positions.iterate_vehicles():
		# print("pro vozidlo")

		# if vehicle.trip_id in trips_black_list:
		# 	continue

		"""
			Try to get id_trip. If trip does not exist returns empty list else  
			returns list where first element is id_trip.
		"""
		try_id_trip = database_connection.execute_fetchall('SELECT id_trip FROM trips WHERE trip_source_id = %s LIMIT 1', (vehicle.trip_id,))

		# Trip has found
		if len(try_id_trip) != 0:
			# print("nalezen")
			vehicle.id_trip = try_id_trip[0][0]

			try:
				# print(str(vehicle.get_tuple_update_trip()))
				database_connection.execute_transaction_commit_rollback('SELECT update_trip_and_insert_coordinates_if_changed(%s, %s, %s, %s, %s, %s);', vehicle.get_tuple_update_trip())
			except IOError as e:
				print("Update trip failed " + str(vehicle.trip_id) + str(e))



		# Trip has not found
		else:
			# print("nenalezen")
			if args.static_data:
				try:
					vehicle.static_get_json_trip_file()
				except FileNotFoundError:
					continue
			else:
				vehicle.get_json_trip_file()

			vehicle.save_shape_file()

			try:
				database_connection.execute('START TRANSACTION;')

				vehicle.id_trip = database_connection.execute_fetchall('SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s)', vehicle.get_tuple_new_trip())[0][0]
				# database_connection.execute_many('INSERT IGNORE INTO rides (id_trip, id_stop, arrival_time, departure_time, shape_dist_traveled) VALUES (%s, %s, %s, %s, %s)', vehicle.get_tuple_new_trip())

				Stops.insert_ride_by_trip(database_connection, vehicle)

				database_connection.execute('COMMIT;')

			# if any exception occuress rollback and save trip to blacklist
			except Exception as e:
				# trips_black_list.add(vehicle.trip_id)
				database_connection.execute('ROLLBACK;')
				print(vehicle.get_tuple_new_trip())
				print("new trip insert failed " + str(vehicle.trip_id) + str(e))
				# TODO osetrit chyby ve vstupech
				if isinstance(e, mysql.connector.errors.IntegrityError):
					print(vehicle.trip_id + " has null delay last stop")
				else:
					raise Exception(e)


	try:
		if not args.static_data:
			time.sleep(args.update_time - (time.time() - req_start))
	except Exception as e:
		print(e)
		# logging.warning("Sleep failed, " + str(e))
		continue
