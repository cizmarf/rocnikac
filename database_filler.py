import argparse
import datetime
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import json
import logging
from pathlib import Path
import mysql.connector

from common_functions import SQL_queries, allFilesURL
from common_functions import URLs
from common_functions import Log
from common_functions import downloadURL
import update_stops


class Trip_current_info:
	def __init__(self, 
				 trip_id: str = None, 
				 lat: str = None, 
				 lon: str = None, 
				 cur_delay: int = None,
				 last_stop_delay = None,
				 shape_traveled: int = None,
				 trip_no: str = None, 
				 time: str = None, 
				 trip_headsign: str = None, 
				 id_trip_headsign: int = None, 
				 id_trip: int = None):
		
		self.id_trip = id_trip
		self.id_trip_headsign = id_trip_headsign
		self.time = time
		self.trip_no = trip_no
		self.shape_traveled = shape_traveled
		self.cur_delay = cur_delay
		self.lon = lon
		self.lat = lat
		self.trip_id = trip_id
		self.trip_headsign = trip_headsign
		self.last_stop_delay = last_stop_delay


"""
			Following function parses multiple optional arguments or sets default value of them
			Learn 'help' arguments for more information
			Returns object of arguments
"""


def parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--log", default="../database_filler.log", type=str, help="Name of logging file")
	parser.add_argument("--trips_folder", default="../data/trips", type=str, help="Name of trips folder")
	args = parser.parse_args()
	return args


def transform_json_to_geojson(json_vehiclepositions: dict) -> dict:
	geojson_vehiclepositions = {}
	geojson_vehiclepositions["type"] = "FeatureCollection"
	geojson_vehiclepositions["timestamp"] = time.strftime("%Y-%m-%d-%H:%M:%S")
	geojson_vehiclepositions["features"] = []

	for bus_input_list in json_vehiclepositions["features"]:
		bus_properties = bus_input_list["properties"]["trip"]
		current_trip_gtfs_id = bus_properties["gtfs_trip_id"]
		bus_output_list = {}
		bus_output_list["type"] = "Feature"
		bus_output_list["properties"] = {}
		bus_output_list["properties"]["gtfs_trip_id"] = current_trip_gtfs_id
		bus_output_list["properties"]["gtfs_route_short_name"] = bus_properties["gtfs_route_short_name"]
		bus_output_list["geometry"] = {}
		bus_output_list["geometry"]["coordinates"] = bus_input_list["geometry"]["coordinates"]
		bus_output_list["geometry"]["type"] = "Point"
		geojson_vehiclepositions["features"].append(bus_output_list)
	return geojson_vehiclepositions


"""
	Gets json data describing shape of given trip and transforms it into geojson 
	file format.
"""


def transform_shape_json_file(old_json_data: dict) -> dict:
	new_json_data = {}
	new_json_data["type"] = "FeatureCollection"
	new_json_data["features"] = [None]
	new_json_data["features"][0] = {}
	new_json_data["features"][0]["type"] = "Feature"
	new_json_data["features"][0]["geometry"] = {}
	new_json_data["features"][0]["geometry"]["type"] = "LineString"
	new_json_data["features"][0]["geometry"]["properties"] = {}
	new_json_data["features"][0]["geometry"]["properties"]["shape_dist_traveled"] = []
	new_json_data["features"][0]["geometry"]["coordinates"] = []
	for feature in old_json_data["shapes"]:
		new_json_data["features"][0]["geometry"]["coordinates"].append(feature["geometry"]["coordinates"])
		new_json_data["features"][0]["geometry"]["properties"]["shape_dist_traveled"].append(format_shape_traveled(feature["properties"]["shape_dist_traveled"]))
	return new_json_data


def update_json_file(json_data: dict, path: str, mode: str, log_message: str):
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


def format_shape_traveled(shape_t: str) -> int:
	return int(float(shape_t) * 1000)


def sleep_if_error_occurs():
	time.sleep(args.update_error - (time.time() - req_start))


if __name__ == "__main__":
	args = parse_arguments()
	logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=args.log, filemode='w')
	logging.info(Log.start)
	stops_updated = datetime.datetime.min

	connection_db = mysql.connector.connect(
		host="localhost",
		database="vehicles_info",
		user="vehicles_access",
		passwd="my_password",
		autocommit=False
	)
	cursor_prepared_db = connection_db.cursor(prepared=True)
	cursor_db = connection_db.cursor()
	"""
		Main loop -- is repeating every {update_time} seconds
	"""
	while True:
		req_start = time.time()

		"""
			Update positions file with priority
		"""
		try:
			json_vehiclepositions = downloadURL(URLs.vehicles_positions)
			update_json_file(
				transform_json_to_geojson(json_vehiclepositions),
				allFilesURL.vehicles_positions,
				"w+",
				Log.vpf_up
			)

		except URLError as e:
			logging.error(Log.net_err + str(e))
			sleep_if_error_occurs()
			continue

		except IOError as e:
			logging.error(Log.io_err + str(e))
			sleep_if_error_occurs()
			continue

		for bus_input_list in json_vehiclepositions["features"]:

			if	bus_input_list["properties"]["trip"]["gtfs_trip_id"] is None or \
				bus_input_list["geometry"]["coordinates"][1] is None or \
				bus_input_list["geometry"]["coordinates"][0] is None or \
				bus_input_list["properties"]["last_position"]["delay"] is None or \
				bus_input_list["properties"]["last_position"]["gtfs_shape_dist_traveled"] is None or \
				bus_input_list["properties"]["trip"]["gtfs_route_short_name"] is None or \
				bus_input_list["properties"]["last_position"]["origin_timestamp"] is None:
					continue

			delay = bus_input_list["properties"]["last_position"]["delay_stop_departure"]

			if bus_input_list["properties"]["last_position"]["delay_stop_departure"] is None:
				delay = bus_input_list["properties"]["last_position"]["delay_stop_arrival"]
				if bus_input_list["properties"]["last_position"]["delay_stop_arrival"] is None:
					continue


			delay = int(delay)

			current_trip = Trip_current_info(
				trip_id=bus_input_list["properties"]["trip"]["gtfs_trip_id"],
				lat=bus_input_list["geometry"]["coordinates"][1],
				lon=bus_input_list["geometry"]["coordinates"][0],
				cur_delay=int(bus_input_list["properties"]["last_position"]["delay"]),
				shape_traveled=format_shape_traveled(bus_input_list["properties"]["last_position"]["gtfs_shape_dist_traveled"]),
				trip_no=bus_input_list["properties"]["trip"]["gtfs_route_short_name"],
				time=bus_input_list["properties"]["last_position"]["origin_timestamp"],
				last_stop_delay=delay,
			)

			try_fetch_id_trip = SQL_queries.sql_get_result(
				cursor_db,
				SQL_queries.S_id_trip_F_trips,
				(current_trip.trip_id,)
			)

			if len(try_fetch_id_trip) != 0:
				current_trip.id_trip = try_fetch_id_trip[0][0]

			# if trip does not exist
			if current_trip.id_trip is None:
				logging.info(Log.new_trip(current_trip.trip_id))

				try:
					json_trip = downloadURL(URLs.trip_by_id(current_trip.trip_id))

				except URLError as e:
					logging.error(Log.net_err + str(e))
					continue  # This jumps to for loop iterating throw all trips in current request.

				current_trip.trip_headsign = json_trip["trip_headsign"]

				# inserts headsign if not exist and return its id -- (!exists <-> insert) & ret id
				current_trip.id_trip_headsign = SQL_queries.sql_run_transaction_and_fetch(
					connection_db, 
					cursor_db, 
					SQL_queries.insert_headsign,
					(current_trip.trip_headsign,)
				)[0][0]

				# inserts trip and return its id
				current_trip.id_trip = SQL_queries.sql_run_transaction_and_fetch(
					connection_db,
					cursor_db, 
					SQL_queries.insert_trip,
					(	current_trip.trip_id,
						current_trip.id_trip_headsign,
						current_trip.last_stop_delay,
						current_trip.shape_traveled, current_trip.trip_no
					)
				)[0][0]

				# insert current coordinates
				SQL_queries.sql_run_transaction(
					connection_db, 
					cursor_prepared_db, 
					SQL_queries.up_trip_coo,
					[(	current_trip.id_trip,
						current_trip.lat, 
						current_trip.lon,
						current_trip.time[:current_trip.time.index(".")],
						current_trip.last_stop_delay,
						current_trip.shape_traveled
					)]
				)

				# TODO reset database

				# creates new ride according to the current trip
				stops_of_trip = []

				for json_stop in json_trip["stop_times"]:
					id_stop = SQL_queries.sql_get_result(
						cursor_db,
						SQL_queries.S_id_stop_F_stops,
						(json_stop["stop_id"],)
					)

					if len(id_stop) > 0:
						id_stop = id_stop[0][0]

					# stop is not in stop table
					else:

						if (datetime.datetime.now() - stops_updated).total_seconds() > 300:
							logging.info(Log.stops_up)
							update_stops.run_update_stops_script()
							id_stop = SQL_queries.sql_get_result(
								cursor_db,
								SQL_queries.S_id_stop_F_stops,
								(json_stop["stop_id"],)
							)
							stops_updated = datetime.datetime.now()

						if len(id_stop) > 0:
							id_stop = id_stop[0][0]

						# stop was not found in the stop file
						else:

							logging.warning(Log.stop_nf)
							stop_id = json_stop["stop_id"]
							lon = json_stop["stop"]["properties"]["stop_lon"]
							lat = json_stop["stop"]["properties"]["stop_lat"]
							stop_name = json_stop["stop"]["properties"]["stop_name"]
							id_stop = SQL_queries.sql_run_transaction_and_fetch(
								connection_db,
								cursor_db,
								SQL_queries.insert_stop,
								(	stop_id,
									stop_name,
									lat,
									lon
								)
							)[0][0]

					stops_of_trip.append((
						current_trip.id_trip,
						id_stop,
						json_stop["arrival_time"],
						json_stop["departure_time"],
						format_shape_traveled(json_stop["shape_dist_traveled"])
					))

				SQL_queries.sql_run_transaction(
					connection_db,
					cursor_prepared_db,
					SQL_queries.insert_ride,
					stops_of_trip
				)

				# produces shape geojson file
				geojson_shape = transform_shape_json_file(json_trip)
				try:
					update_json_file(
						geojson_shape,
						Path(args.trips_folder) / (current_trip.trip_id + ".shape"),
						"w+",
						Log.new_shape(current_trip.trip_id)
					)

				except IOError as e:
					logging.error(Log.io_err + str(e))
					time.sleep(args.update_error - (time.time() - req_start))
					continue  # This jumps to for loop iterating throw all trips in current request.

			# trip exists
			else:
				# updates trip data
				SQL_queries.sql_run_transaction(
					connection_db, 
					cursor_prepared_db, 
					SQL_queries.up_trip, 
					[(	current_trip.last_stop_delay,
						current_trip.shape_traveled, 
						current_trip.id_trip
					)]
				)

				logging.info("Trip " + current_trip.trip_id + " updated")


				# insert current coordinates + check if bus_time changed
				last_trip_time = ""
				try:
					last_trip_time = SQL_queries.sql_get_result(
						cursor_db,
						SQL_queries.S_id_trip_F_coor,
						(current_trip.id_trip,)
					)[0][0]
				except IndexError:
					logging.warning("Trip coor not found.")

				dt_c_trip = datetime.datetime.strptime(current_trip.time[:current_trip.time.index(".")], "%Y-%m-%dT%H:%M:%S")

				if dt_c_trip != last_trip_time:
					SQL_queries.sql_run_transaction(
						connection_db,
						cursor_prepared_db,
						SQL_queries.up_trip_coo,
						[(	current_trip.id_trip,
							current_trip.lat,
							current_trip.lon,
							current_trip.time[:current_trip.time.index(".")],
							current_trip.last_stop_delay,
							current_trip.shape_traveled
						)]
					)

		"""
			Following code tries to sleep {update_time} - seconds consumed above
			if fails the main loop is repeated immediately
		"""
		try:
			time.sleep(args.update_time - (time.time() - req_start))
		except Exception as e:
			logging.warning("Sleep failed, " + str(e))
			continue
