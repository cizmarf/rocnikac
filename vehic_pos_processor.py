import argparse
import asyncio
import datetime
import time
import json
import logging
import os

from pathlib import Path, PosixPath
from collections import deque
from urllib.error import URLError
from urllib.request import Request, urlopen

# geojson indexes names
import async_timeout
from aiohttp import ClientSession
from common_functions import GI


# logging messages
class Log:
	start = "Program has started."
	net_err = "Network error: "
	sleep = "Sleep failed, "
	io_err = "Write to file failed: "
	vpf_up = "Vehicle positions file updated"

	@staticmethod
	def trip_updater(trip_id: str) -> str:
		return "Trip " + trip_id + " positions file updated"

	@staticmethod
	def del_files(trip: str) -> str:
		return "Shape of trip " + trip + " file removed"

	@staticmethod
	def deL_fail(trip: str) -> str:
		return "Some file for trip " + trip + " not found."

	@staticmethod
	def new_shape(trip: str) -> str:
		return "New shape of trip " + trip + " file exported"


def update_json_file(json_data: dict, path, log_message: str, mode: str = "w+") -> None:
	try:
		with open(path, mode) as f:
			f.seek(0)
			f.write(json.dumps(json_data))
			if log_message != "":
				logging.info(log_message)

	except Exception as e:
		raise IOError(e)

	finally:
		f.close()


def downloadURL(request: Request) -> dict:
	webURL = urlopen(request)
	response_body = webURL.read()
	encoding = webURL.info().get_content_charset('utf-8')
	return json.loads(response_body.decode(encoding))


def prepare_geojson_lfms() -> dict:
	geojson_lfms = {}
	geojson_lfms[ GI.type ] = GI.featureCollection
	geojson_lfms[ GI.features ] = [ {} ]
	geojson_lfms[ GI.features ][ 0 ][ GI.type ] = GI.feature
	geojson_lfms[ GI.features ][ 0 ][ GI.properties ] = {}
	geojson_lfms[ GI.features ][ 0 ][ GI.geometry ] = {}
	geojson_lfms[ GI.features ][ 0 ][ GI.geometry ][ GI.type ] = GI.lineString
	geojson_lfms[ GI.features ][ 0 ][ GI.geometry ][ GI.coordinates ] = [ ]
	return geojson_lfms


def transform_bus_list(bus_input_list: dict) -> dict:
	bus_properties = bus_input_list[ GI.properties ][ GI.trip ]
	current_trip_gtfs_id = bus_properties[ GI.gtfs_trip_id ]
	bus_output_list = {}
	bus_output_list[ GI.type ] = GI.feature
	bus_output_list[ GI.properties ] = {}
	bus_output_list[ GI.properties ][ GI.gtfs_trip_id ] = current_trip_gtfs_id
	bus_output_list[ GI.properties ][ GI.gtfs_route_short_name ] = bus_properties[ GI.gtfs_route_short_name ]
	bus_output_list[ GI.geometry ] = {}
	bus_output_list[ GI.geometry ][ GI.coordinates ] = bus_input_list[ GI.geometry ][ GI.coordinates ]
	bus_output_list[ GI.geometry ][ GI.type ] = "Point"
	return bus_output_list


def transform_shape_json_file(old_json_data: dict) -> dict:
	new_json_data = {}
	new_json_data[ GI.type ] = GI.featureCollection
	new_json_data[ GI.features ] = [ None ]
	new_json_data[ GI.features ][ 0 ] = {}
	new_json_data[ GI.features ][ 0 ][ GI.type ] = GI.feature
	new_json_data[ GI.features ][ 0 ][ GI.geometry ] = {}
	new_json_data[ GI.features ][ 0 ][ GI.geometry ][ GI.type ] = GI.lineString
	new_json_data[ GI.features ][ 0 ][ GI.geometry ][ GI.properties ] = {}
	new_json_data[ GI.features ][ 0 ][ GI.geometry ][ GI.coordinates ] = [ ]
	for feature in old_json_data[ GI.shapes ]:
		new_json_data[ GI.features ][ 0 ][ GI.geometry ][ GI.coordinates ].append(
			feature[ GI.geometry ][ GI.coordinates ])
	return new_json_data


def is_old(coordinates: list) -> bool:
	from datetime import datetime
	fmt = '%H:%M:%S'
	coordinates_time = coordinates[ 1 ]
	now = datetime.now().strftime(fmt)
	tdelta = datetime.strptime(now, fmt) - datetime.strptime(coordinates_time, fmt)
	seconds = tdelta.total_seconds()
	if seconds > 10 * 60:
		return True
	return False


def create_shape_file(trip: str, current_trips_set: set, json_data_trip: dict) -> None:
	try:
		geojson_shape = transform_shape_json_file(json_data_trip)
		update_json_file(geojson_shape, Path(args.trips_folder) / (trip + ".shape"), Log.new_shape(trip))
	except URLError as e:
		logging.error(Log.net_err + str(e))
		current_trips_set -= trip
		raise ValueError
	except IOError as e:
		logging.error(Log.io_err + str(e))
		current_trips_set -= trip
		raise ValueError


async def get_html(trip: str, current_trips_set: set, active_trips_set: set, active_trips: dict, session: ClientSession, url: str) -> None:
	try:
		with async_timeout.timeout(10):
			async with session.get(url) as response:
				chunk = await response.content.read()
				json_data_trip = json.loads(chunk.decode())

				if trip in current_trips_set - active_trips_set:
					create_shape_file(trip, current_trips_set, json_data_trip)

				geojson_lfms = prepare_geojson_lfms()
				if len(active_trips[ trip ]) > 0:
					geojson_lfms[ GI.features ][ 0 ][ GI.geometry ][ GI.coordinates ].append(
						active_trips[ trip ][ 0 ][ 0 ])

					for shape_fault in json_data_trip[ GI.shapes ]:
						if float(shape_fault[ GI.properties ][ GI.shape_dist_traveled ]) > float(
								active_trips[ trip ][ 0 ][ 2 ]) and float(
							shape_fault[ GI.properties ][ GI.shape_dist_traveled ]) < float(
							active_trips[ trip ][ len(active_trips[ trip ]) - 1 ][ 2 ]):
							geojson_lfms[ GI.features ][ 0 ][ GI.geometry ][ GI.coordinates ].append(
								shape_fault[ GI.geometry ][ GI.coordinates ])

					geojson_lfms[ GI.features ][ 0 ][ GI.geometry ][ GI.coordinates ].append(
						active_trips[ trip ][ len(active_trips[ trip ]) - 1 ][ 0 ])

				# if trip == "395_66_190902":
				# 	print(pom_coo, " ", active_trips[trip][len(active_trips[trip]) - 1][0])
				update_json_file(geojson_lfms, Path(args.trips_folder) / (trip + '.lfms'), Log.trip_updater(trip))
	except URLError as e:
		logging.error(Log.net_err + str(e))
		current_trips_set -= trip
	except IOError as e:
		logging.error(Log.io_err + str(e))
		current_trips_set -= trip
	except ValueError:
		pass


async def for_trips_asy(current_trips_set: set, active_trips_set: set, active_trips: dict) -> None:
	async with ClientSession(headers=headers) as session:
		if '395_241_190902' in current_trips_set:
			print("ano")
		tasks = [ get_html(trip, current_trips_set, active_trips_set, active_trips, session,
						   'https://api.golemio.cz/v1/gtfs/trips/' + trip + '?includeShapes=true') for trip in
				  current_trips_set ]
		await asyncio.wait(tasks)


def parse_arguments() -> argparse.Namespace:
	parser = argparse.ArgumentParser()
	parser.add_argument("--file_name", default="../data/veh_act_pos", type=str, help="The last generated output file")
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--log", default="../veh_pos_proc.log", type=str, help="Name of logging file")
	parser.add_argument("--trips_folder", default="../data/trips", type=str, help="Name of trips folder")
	return parser.parse_args()


"""
	Following header is necessary for requesting golemio api.
	code copied from https://golemioapi.docs.apiary.io/#reference/public-transport/vehicle-positions/get-all-vehicle-positions
	access token generated by https://api.golemio.cz/api-keys/auth/sign-in
	Get your own token!
"""
headers = {
	'Content-Type': 'application/json; charset=utf-8',
	'x-access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNpem1hcmZpbGlwQGdtYWlsLmNvbSIsImlkIjo3NiwibmFtZSI6bnVsbCwic3VybmFtZSI6bnVsbCwiaWF0IjoxNTcwNTQ2MTU2LCJleHAiOjExNTcwNTQ2MTU2LCJpc3MiOiJnb2xlbWlvIiwianRpIjoiMzAxYWNhNDUtNGRlNC00ZDRmLWI4NzAtMzQwMDQ5OTM1MzBhIn0.4rCELzCNY8XOSvjqQA7cKocPGJ8D2ezhXiWUkIRUNjg'
}

if __name__ == "__main__":

	args = parse_arguments()
	logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=args.log,
						filemode='w')
	logging.info(Log.start)

	active_trips = {key[ :-6 ]: deque() for key in os.listdir(args.trips_folder) if key.endswith('.shape')}
	active_trips_set = {key[ :-6 ] for key in os.listdir(args.trips_folder) if key.endswith('.shape')}
	# pom_coo = ""
	while True:

		# Download the updated information about buses and store them in the json_data array.
		req_start = time.time()
		try:
			json_vehiclepositions = downloadURL(Request('https://api.golemio.cz/v1/vehiclepositions', headers=headers))
		except URLError as e:
			logging.error(Log.net_err + str(e))
			time.sleep(args.update_error - (time.time() - req_start))
			continue

		# Process json data and generate geojson file
		geojson_vehiclepositions = {}
		geojson_vehiclepositions[ GI.type ] = GI.featureCollection
		geojson_vehiclepositions[ "timestamp" ] = time.strftime("%Y-%m-%d-%H:%M:%S")
		geojson_vehiclepositions[ GI.features ] = [ ]

		current_trips_set = set()
		for bus_input_list in json_vehiclepositions[ GI.features ]:
			geojson_vehiclepositions[ GI.features ].append(transform_bus_list(bus_input_list))
			current_trip_gtfs_id = bus_input_list[ GI.properties ][ GI.trip ][ GI.gtfs_trip_id ]
			current_trips_set.add(current_trip_gtfs_id)

			# if bus_input_list[GI.properties][GI.trip][GI.gtfs_trip_id] == "395_66_190902":
			# 	pom_coo = bus_input_list[GI.geometry][GI.coordinates]

			"""
				active_trips variable holds all positions of each trip for last n seconds (defined in function is_old).
				The following code update the bus positions information in the variable. 
			"""

			if current_trip_gtfs_id not in active_trips or len(active_trips[ current_trip_gtfs_id ]) == 0:
				active_trips[ current_trip_gtfs_id ] = deque()
				active_trips[ current_trip_gtfs_id ].append([ bus_input_list[ GI.geometry ][ GI.coordinates ],
															  bus_input_list[ GI.properties ][ "last_position" ][
																  "origin_time" ],
															  bus_input_list[ GI.properties ][ "last_position" ][
																  "gtfs_shape_dist_traveled" ] ])
			else:
				active_trips[ current_trip_gtfs_id ].append([ bus_input_list[ GI.geometry ][ GI.coordinates ],
															  bus_input_list[ GI.properties ][ "last_position" ][
																  "origin_time" ],
															  bus_input_list[ GI.properties ][ "last_position" ][
																  "gtfs_shape_dist_traveled" ] ])
				while len(active_trips[ current_trip_gtfs_id ]) > 0 and is_old(
						active_trips[ current_trip_gtfs_id ][ 0 ]):
					active_trips[ current_trip_gtfs_id ].popleft()

		try:
			update_json_file(geojson_vehiclepositions, Path(args.file_name), Log.vpf_up)
		except IOError as e:
			logging.error(Log.io_err + str(e))
			continue

		for trip in active_trips_set - current_trips_set:
			active_trips.pop(trip)
			try:
				os.remove(Path(args.trips_folder) / (trip + ".shape"))
				os.remove(Path(args.trips_folder) / (trip + ".lfms"))
				logging.info(Log.del_files(trip))
			except FileNotFoundError as e:
				logging.warning(Log.deL_fail(trip))

		asyncio.run(for_trips_asy(current_trips_set, active_trips_set, active_trips))
		# eventLoop = asyncio.get_event_loop()
		# eventLoop.run_until_complete(for_trips_asy(current_trips_set, active_trips_set, active_trips))
		# eventLoop.close()

		active_trips_set = current_trips_set

		# try:
		p_sleep = args.update_time - (time.time() - req_start)
		if p_sleep > 0:
			time.sleep(args.update_time - (time.time() - req_start))
		# except Exception as e:
		# 	logging.warning(Log.sleep + str(e))
		# 	continue
