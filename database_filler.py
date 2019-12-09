import argparse
import datetime
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import json
import logging
from pathlib import Path
import mysql.connector

from common_functions import headers
from common_functions import downloadURL
from common_functions import sql_run_transaction_and_fetch
from common_functions import sql_run_transaction
from common_functions import sql_get_result
import update_stops


# logging messages
class Log:
	start = 	"Program has started."
	net_err = 	"Network error: "
	sleep = 	"Sleep failed, "
	io_err = 	"Write to file failed: "
	vpf_up = 	"Vehicle positions file updated"
	stops_up =	"Stops are updating"
	stop_nf = 	"Stop was not found in stops file"


	@staticmethod
	def new_trip(trip_id):
		return "New trip " + trip_id + " found"

"""
			Following function parses multiple optional arguments or sets default value of them
			Learn 'help' arguments for more information
			Returns object of arguments
"""
def parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("--veh_act_pos_fn", default="../data/veh_act_pos", type=str,
						help="The last generated output file")
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--log", default="../database_filler.log", type=str, help="Name of logging file")
	parser.add_argument("--trips_folder", default="../data/trips", type=str, help="Name of trips folder")
	args = parser.parse_args()
	return args


"""
	Returns geojson object
"""
def transform_json_to_geojson(json_vehiclepositions):
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
def transform_shape_json_file(old_json_data):
	new_json_data = {}
	new_json_data["type"] = "FeatureCollection"
	new_json_data["features"] = [None]
	new_json_data["features"][0] = {}
	new_json_data["features"][0]["type"] = "Feature"
	new_json_data["features"][0]["geometry"] = {}
	new_json_data["features"][0]["geometry"]["type"] = "LineString"
	new_json_data["features"][0]["geometry"]["properties"] = {}
	new_json_data["features"][0]["geometry"]["coordinates"] = []
	for feature in old_json_data["shapes"]:
		new_json_data["features"][0]["geometry"]["coordinates"].append(feature["geometry"]["coordinates"])
	return new_json_data


def update_json_file(json_data, path, mode, log_message):
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


def format_shape_traveled(shape_t):
	return int(float(shape_t) * 1000)


if __name__ == "__main__":
	args = parse_arguments()
	logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=args.log,
						filemode='w')
	logging.info(Log.start)
	stops_updated = datetime.datetime.min

	connection_db = mysql.connector.connect(
		host="localhost",
		database="vehicles_info",
		user="vehicles_access",
		passwd="my_password",
		autocommit = False
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
			json_vehiclepositions = downloadURL(Request('https://api.golemio.cz/v1/vehiclepositions', headers=headers))
			update_json_file(transform_json_to_geojson(json_vehiclepositions), Path(args.veh_act_pos_fn), "w+", Log.vpf_up)
		except URLError as e:
			logging.error(Log.net_err + str(e))
			time.sleep(args.update_error - (time.time() - req_start))
			continue
		except IOError as e:
			logging.error(Log.io_err + str(e))
			time.sleep(args.update_error - (time.time() - req_start))
			continue

		for bus_input_list in json_vehiclepositions["features"]:
			# TODO Trip id se musi zahashovat pro effectivni vyhledavani v databazi
			trip_id = bus_input_list["properties"]["trip"]["gtfs_trip_id"]
			id_trip = sql_get_result(cursor_db, 'SELECT id_trip FROM trips WHERE trip_id = %s LIMIT 1', (trip_id,))

			delay = int(bus_input_list["properties"]["last_position"]["delay"])
			shape_traveled = format_shape_traveled(bus_input_list["properties"]["last_position"]["gtfs_shape_dist_traveled"])
			trip_no = bus_input_list["properties"]["trip"]["cis_short_name"]
			bus_lat = bus_input_list["geometry"]["coordinates"][1]
			bus_lon = bus_input_list["geometry"]["coordinates"][0]
			bus_time = bus_input_list["properties"]["last_position"]["origin_timestamp"]

			# if trip does not exist
			if len(id_trip) == 0:
				logging.info(Log.new_trip(trip_id))
				try:
					json_trip = downloadURL(Request('https://api.golemio.cz/v1/gtfs/trips/' + trip_id + '?includeShapes=true&includeStopTimes=true&includeStops=true', headers=headers))
				except URLError as e:
					logging.error(Log.net_err + str(e))
					continue  # This jumps to for loop iterating throw all trips in current request.

				trip_headsign = json_trip["trip_headsign"]

				# inserts headsign if not exist and return its id -- (!exists <-> insert) & ret id
				id_headsign = sql_run_transaction_and_fetch(connection_db, cursor_db, 'SELECT insert_headsign_if_exists_and_return_id(%s)', (trip_headsign, ))[0][0]

				# inserts trip and return its id
				id_trip = sql_run_transaction_and_fetch(connection_db, cursor_db, 'SELECT insert_trip_and_return_id (%s, %s, %s, %s, %s)', (trip_id, id_headsign, delay, shape_traveled, trip_no))[0][0]

				# creates new ride according to the current trip
				stops_of_trip = []
				for json_stop in json_trip["stop_times"]:
					id_stop = sql_get_result(cursor_db, 'SELECT id_stop FROM stops WHERE stop_id = %s', (json_stop["stop_id"],))
					if len(id_stop) > 0:
						id_stop = id_stop[0][0]

					# stop is not in stop table
					else:
						if (datetime.datetime.now() - stops_updated).total_seconds() > 300:
							logging.info(Log.stops_up)
							update_stops.run_update_stops_script()
							id_stop = sql_get_result(cursor_db, 'SELECT id_stop FROM stops WHERE stop_id = %s', (json_stop["stop_id"],))
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
								id_stop = sql_run_transaction_and_fetch(connection_db, cursor_db,
																		'SELECT insert_stop_and_return_id (%s, %s, %s, %s, NULL)',
																		(stop_id, stop_name, lat, lon))[0][0]


						# stop was not found in the stop file
						else:
							logging.warning(Log.stop_nf)
							stop_id = json_stop["stop_id"]
							lon = json_stop["stop"]["properties"]["stop_lon"]
							lat = json_stop["stop"]["properties"]["stop_lat"]
							stop_name = json_stop["stop"]["properties"]["stop_name"]
							id_stop = sql_run_transaction_and_fetch(connection_db, cursor_db, 'SELECT insert_stop_and_return_id (%s, %s, %s, %s, NULL)', (stop_id, stop_name, lat, lon))[0][0]

					stops_of_trip.append((id_trip, id_stop, json_stop["arrival_time"], json_stop["departure_time"], format_shape_traveled(json_stop["shape_dist_traveled"])))

				sql_run_transaction(connection_db, cursor_prepared_db, 'INSERT INTO rides (id_trip, id_stop, arrival_time, departure_time, shape_dist_traveled) VALUES (%s, %s, %s, %s, %s)', stops_of_trip)

				# produces shape geojson file
				geojson_shape = transform_shape_json_file(json_trip)
				try:
					update_json_file(geojson_shape, Path(args.trips_folder) / (trip_id + ".shape"), "w+", "New shape of trip " + trip_id + " file exported")

				except IOError as e:
					logging.error(Log.io_err + str(e))
					time.sleep(args.update_error - (time.time() - req_start))
					continue  # This jumps to for loop iterating throw all trips in current request.
			# trip exists
			else:
				id_trip = id_trip[0][0]

				# updates trip data
				sql_run_transaction(connection_db, cursor_prepared_db, 'UPDATE trips SET current_delay = %s, shape_traveled = %s WHERE id_trip = %s', [(delay, shape_traveled, id_trip)])
				logging.info("Trip" + trip_id + "updated")

			# insert current coordinates
			sql_run_transaction(connection_db, cursor_prepared_db, 'INSERT INTO trip_coordinates (id_trip, lat, lon, time, delay, shape_traveled) VALUES (%s, %s, %s, %s, %s, %s)', [(id_trip, bus_lat, bus_lon, bus_time[:bus_time.index(".")], delay, shape_traveled)])


		"""
			Following code tries to sleep {update_time} - time consumed above seconds
			if fails the main loop is repeated immediately
		"""
		try:
			time.sleep(args.update_time - (time.time() - req_start))
		except Exception as e:
			logging.warning("Sleep failed, " + str(e))
			continue

