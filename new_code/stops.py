import argparse
import logging

from database import Database
from network import Network
from trip import Trip


class Stops:

	@staticmethod
	def insert_ride_by_trip(database_connection, vehicle):
		stops = Stops.Dictlist()

		for jstop in vehicle.json_trip["stop_times"]:
			stop_id = jstop["stop"]["properties"]["stop_id"]
			stop_parent_id = jstop["stop"]["properties"]["parent_station"]
			lon = jstop["stop"]["properties"]["stop_lon"]
			lat = jstop["stop"]["properties"]["stop_lat"]
			stop_name = jstop["stop"]["properties"]["stop_name"]
			stop = [stop_id, stop_name, lat, lon]
			stops[stop_parent_id] = stop

		# inserts all stops of trip ride
		# there is no info about stop parents in stop times dictionary
		Stops.insert(database_connection, stops, stops[""], 'NULL', '')

		stops_of_trip = []
		for json_stop in vehicle.json_trip["stop_times"]:
			stop_id = json_stop["stop_id"]
			id_stop = database_connection.execute_fetchall("""
				SELECT id_stop 
				FROM stops 
				WHERE stop_source_id = %s""",
				(stop_id, ))[0][0]

			stops_of_trip.append((
				vehicle.id_trip,
				id_stop,
				json_stop["arrival_time"],
				json_stop["departure_time"],
				Trip.format_shape_traveled(json_stop["shape_dist_traveled"])
			))

		database_connection.execute_many("""
			INSERT INTO rides (
				id_trip, id_stop, arrival_time, departure_time, shape_dist_traveled) 
			VALUES (%s, %s, %s, %s, %s)""",
			stops_of_trip)

	# appends value to list in proper element of dict,
	# creates new dict element if not exists
	class Dictlist(dict):
		def __setitem__(self, key, value):
			if key not in self:
				super(Stops.Dictlist, self).__setitem__(key, [])
			self[key].append(value)

	# recursive function inserting all stops and for each stop its descendant recursively
	@staticmethod
	def insert(database_connection, stops, to_insert, id_parent, parent_id):

		del stops[parent_id]
		database_connection.execute_many("""
			INSERT IGNORE INTO stops (
				stop_source_id, stop_name, lat, lon, parent_id_stop) 
			VALUES (%s, %s, %s, %s, ' + str(id_parent) + ')"""
			, [tuple(t) for t in to_insert])

		# insert all descendants
		for e in to_insert:
			if e[0] in stops:
				Stops.insert(
					database_connection,
					stops,
					stops[e[0]],
					database_connection.execute_fetchall("""
						SELECT id_stop 
						FROM stops 
						WHERE stop_source_id = %s""",
					(e[0], ))[0][0],
					e[0]
				)

	@staticmethod
	def number_of_stops(json_stops) -> int:
		return len(json_stops['features'])

	# deprecated
	@staticmethod
	def run_update_stops_script(limit: int = 10000):
		database_connection = Database()
		offset = 0
		temp_json_stops = Network.download_URL_to_json(Network.stops(limit))
		json_stops = temp_json_stops

		while Stops.number_of_stops(temp_json_stops) > 0:
			offset += limit
			temp_json_stops = Network.download_URL_to_json(
				Network.stops(limit, offset))
			json_stops['features'].extend(temp_json_stops['features'])

		stops = Stops.Dictlist()

		for jstop in json_stops["features"]:
			stop_id = jstop["properties"]["stop_id"]
			stop_parent_id = jstop["properties"]["parent_station"]
			lon = jstop["geometry"]["coordinates"][0]
			lat = jstop["geometry"]["coordinates"][1]
			stop_name = jstop["properties"]["stop_name"]
			stop = [stop_id, stop_name, lat, lon]
			stops[stop_parent_id] = stop

		Stops.insert(database_connection, stops, stops[""], 'NULL', '')


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--log", default="../stop_update.log", type=str,
		help="Name of log file")
	args = parser.parse_args()

	logging.basicConfig(
		format='%(asctime)s %(levelname)s: %(message)s',
		level=logging.INFO,
		filename=args.log,
		filemode='w')
	logging.info("Program has started")

	Stops.run_update_stops_script()

	logging.info("Program has finished")
