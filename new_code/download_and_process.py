#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
from datetime import datetime
import time
import sys
from os.path import dirname, abspath, join

import mysql.connector

from all_vehicle_positions import All_vehicle_positions, Static_all_vehicle_positions
# from all_vehicle_positions import All_vehicle_positions
from database import Database
from stops import Stops
from trip import Trip
from two_stops_model import *
import lib

from file_system import File_system


def estimate_delays(all_vehicle_positions: All_vehicle_positions, models, database_connection):
	for vehicle in all_vehicle_positions.iterate_vehicles():
		# gets model from given set, if no model found uses linear model by default
		model = models.get(
			str(vehicle.last_stop or '') + "_" + str(vehicle.next_stop or '') + ("_bss" if lib.is_business_day(vehicle.last_updated) else "_hol"),
			Two_stops_model.Linear_model(vehicle.stop_dist_diff))

		tuple_for_predict = vehicle.get_tuple_for_predict()
		if tuple_for_predict is not None:
			vehicle.cur_delay = model.predict(*tuple_for_predict)

		# else it uses last stop delay, set in trips construction


async def update_or_insert_trip(vehicle, database_connection, args):
	# Tries to get id_trip. If trip does not exist returns empty list else
	# returns list where first element is id_trip.
	try_id_trip = database_connection.execute_fetchall('SELECT id_trip FROM trips WHERE trip_source_id = %s LIMIT 1', (vehicle.trip_id,))

	# Trip found
	if len(try_id_trip) != 0:
		vehicle.id_trip = try_id_trip[0][0]

		# Updates database row of current trip and adds new record of historical data
		try:
			if vehicle.cur_delay is None:
				pass # the vehicle have not started its trip yet
			else:
				database_connection.execute_transaction_commit_rollback(
					'SELECT update_trip_and_insert_coordinates_if_changed(%s, %s, %s, %s, %s, %s, %s);',
					vehicle.get_tuple_update_trip(args.static_demo))
		except IOError as e:
			logging.warning("Update trip failed " + str(vehicle.trip_id) + str(e))
			# raise Exception(e)

	# Trip not found
	else:
		# Chooses trip source file (demo/production)
		if args.static_data:
			try:
				vehicle.static_get_json_trip_file()
			except FileNotFoundError:
				return
		else:
			# print("async download started trip id: " + vehicle.trip_id + " time: " + str(datetime.now()))
			await vehicle.get_async_json_trip_file()
			# print("async download finished trip id: " + vehicle.trip_id + " time: " + str(datetime.now()))

		try:
			# Saves shape of current trip into specific folder
			# vehicle.save_shape_file() TODO UNCOMMENT

			database_connection.execute('START TRANSACTION;')
			vehicle.id_trip = database_connection.execute_fetchall(
				'SELECT insert_new_trip_to_trips_and_coordinates_and_return_id(%s, %s, %s, %s, %s, %s, %s, %s, %s)',
				vehicle.get_tuple_new_trip(args.static_demo))[0][0]
			Stops.insert_ride_by_trip(database_connection, vehicle)
			database_connection.execute('COMMIT;')

		# if any exception occurs rollback and save trip to blacklist
		except Exception as e:
			database_connection.execute('ROLLBACK;')
			if isinstance(e, mysql.connector.errors.IntegrityError):
				print(vehicle.trip_id + " has null delay last stop")
			# raise Exception(e)

async def process_async_vehicles(all_vehicle_positions, database_connection, args):
	# Iterates for all vehicles found in source file
	gather = []
	for vehicle in all_vehicle_positions.iterate_vehicles():
		try:
			# if vehicle.trip_no == "317" or vehicle.trip_no == "303":
			gather.append(update_or_insert_trip(vehicle, database_connection, args))
		except Exception as e:
			logging.warning("Trip update failed " + vehicle.trip_id + ". Exception: " + str(e))

	await asyncio.gather(*gather)


def main(database_connection, args):

	models = File_system.load_all_models()

	# For static data source only
	static_iterator = None
	if args.static_data:
		static_all_vehicle_positions = Static_all_vehicle_positions()
		static_iterator = static_all_vehicle_positions.static_get_all_vehicle_positions_json()

	# The main loop
	while True:
		req_start = time.time()  # Time of beginning of a new iteration
		all_vehicle_positions = All_vehicle_positions()  # Class for managing source file data

		# Chooses source file (demo/production)
		if args.static_data:
			try:
				all_vehicle_positions.json_file = next(static_iterator)
			except StopIteration:
				break
		else:
			all_vehicle_positions.get_all_vehicle_positions_json()

		all_vehicle_positions.construct_all_trips(database_connection)  # Creates class for each trip in current source file

		estimate_delays(all_vehicle_positions, models, database_connection)

		# all_vehicle_positions.get_all_vehicle_positions_json()

		# asyncio.run(as_print([1,2,3]))

		asyncio.run(process_async_vehicles(all_vehicle_positions, database_connection, args))

		try:
			if args.static_demo or not args.static_data:
				time.sleep(args.update_time - (time.time() - req_start))
		except Exception as e:
			print(e)
			logging.warning("Sleep failed, " + str(e))
			continue

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--static_data", default=True, type=bool, help="Fill with static data or dynamic real-time data.")
	parser.add_argument("--static_demo", default=False, type=bool,
						help="Use only if static data in use, time of insert sets now and wait 20 s for next file.")
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--clean_old", default=-1, type=int, help="Deletes all trips inactive for more than set minutes")
	args = parser.parse_args([] if "__file__" not in globals() else None)

	database_connection = Database()

	if args.clean_old != -1:
		ids_to_delete = database_connection.execute_procedure_fetchall("delete_trips_older_than_and_return_their_trip_id", (args.clean_old,))
		for id in ids_to_delete:
			File_system.delete_file(File_system.all_shapes / (id[0] + '.shape'))
		sys.exit(0)

	main(database_connection, args)