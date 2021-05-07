import argparse
from urllib.parse import unquote, quote
from datetime import datetime
import json
import logging
import sys
import threading
import time
from wsgiref.simple_server import make_server
from ftfy import fix_text

from database import Database
from file_system import File_system

class Server:

	def __init__(self, database_name: str = 'vehicle_positions_database'):
		self.database_connection = Database(database_name)
		self.trip_id_to_id_trip_map = {}
		self.FILE = 'index.html'
		self.PORT = 8080

	# returns database id according to the given trip source id
	def get_id_trip_by_trip_id(self, trip_id):

		# looks for trip id in buffer map
		if trip_id in self.trip_id_to_id_trip_map:
			return self.trip_id_to_id_trip_map[trip_id]

		else:
			try:
				print("getting trip id:",  trip_id)
				id_trip = self.database_connection.execute_fetchall("""
					SELECT id_trip 
						FROM trips 
						WHERE trip_source_id = %s LIMIT 1""",
					(trip_id,)
				)[0][0]

				# saves pair to the catch map for faster lookup next time
				self.trip_id_to_id_trip_map[trip_id] = id_trip
				return id_trip

			# index error indicate no response from database
			except IndexError:
				logging.error("Trip", trip_id, "is not in database.")
				return -1

	def get_vehicles_positions(self):
		trips = self.database_connection.execute_fetchall("""
			SELECT 
				trips.trip_source_id, 
				trips.trip_no, 
				headsigns.headsign, 
				trips.current_delay, 
				trips.lat, 
				trips.lon 
			FROM trips 
			JOIN headsigns ON trips.id_headsign = headsigns.id_headsign AND trips.last_updated > NOW() - INTERVAL 10 MINUTE""")

		trips_geojson = {}
		trips_geojson["type"] = "FeatureCollection"
		trips_geojson["features"] = []
		for trip in trips:
			bus_output = {}
			bus_output["type"] = "Feature"
			bus_output["properties"] = {}
			bus_output["properties"]["gtfs_trip_id"] = trip[0]
			bus_output["properties"]["gtfs_route_short_name"] = trip[1]
			bus_output["properties"]["headsign"] = trip[2]
			bus_output["properties"]["delay"] = trip[3]
			bus_output["geometry"] = {}
			bus_output["geometry"]["coordinates"] = [float(trip[5]), float(trip[4])]
			bus_output["geometry"]["type"] = "Point"

			trips_geojson["features"].append(bus_output)

		return trips_geojson

	def prepare_geojson_tail(self):
		geojson_tail = {}
		geojson_tail["type"] = "FeatureCollection"
		geojson_tail["features"] = [{}]
		geojson_tail["features"][0]["type"] = "Feature"
		geojson_tail["features"][0]["properties"] = {}
		geojson_tail["features"][0]["geometry"] = {}
		geojson_tail["features"][0]["geometry"]["type"] = "LineString"
		geojson_tail["features"][0]["geometry"]["coordinates"] = []
		return geojson_tail

	def get_tail(self, trip_id: str, semi_now: datetime = 'now'):

		if semi_now == 'now':
			semi_now = datetime.now()

		# reads trips shape file
		with open((File_system.all_shapes / trip_id).with_suffix(".shape"), "r") as f:
			shape = json.loads(f.read())
			id_trip = self.get_id_trip_by_trip_id(trip_id)

			# selects all trips coordinates data of the given trip created in last 5 mins
			coordinates = self.database_connection.execute_fetchall("""
				SELECT 
					lon, 
					lat, 
					shape_dist_traveled 
				FROM trip_coordinates 
				WHERE trip_coordinates.id_trip = %s 
				AND trip_coordinates.inserted > DATE_SUB(%s, INTERVAL 5 MINUTE) 
				ORDER BY trip_coordinates.inserted""",
				(id_trip, semi_now)
			)

			geojson_tail = self.prepare_geojson_tail()

			if len(coordinates) > 0:
				# appends first returned row from database
				geojson_tail["features"][0]["geometry"]["coordinates"].append(
					[float(coordinates[0][0]), float(coordinates[0][1])])

				# steps over shapes from shape file
				# because we do not really care about addition points from vehicles positions
				for i in range(len(shape["features"][0]["geometry"]["coordinates"])):
					shape_fault = shape["features"][0]["geometry"]["coordinates"][i]
					shape_dist_traveled = \
						shape["features"][0]["geometry"]["properties"]["shape_dist_traveled"][i]

					# appends shape faults if it is between last and last - 5 mins positions of the trip
					if float(coordinates[0][2]) < float(shape_dist_traveled) < float(coordinates[-1][2]):
						geojson_tail["features"][0]["geometry"]["coordinates"].append(shape_fault)

				# appends the last known position of given trip
				geojson_tail["features"][0]["geometry"]["coordinates"].append(
					[float(coordinates[-1][0]), float(coordinates[-1][1])])

			return geojson_tail


	def get_shape(self, trip_id):
		# invalid input
		if '.' in trip_id:
			return ""

		# reads shape file of the given trips
		with open((File_system.all_shapes / trip_id).with_suffix(".shape"), "r") as f:
			shape = json.loads(f.read())
			shape["features"][0]["geometry"]["properties"] = {}
			shape["features"][0]["properties"] = {}

			return shape

	def get_stops(self, trip_id):
		id_trip = self.get_id_trip_by_trip_id(trip_id)

		# selects timetable of the given trip
		stops = self.database_connection.execute_fetchall("""
			SELECT 
				stops.lon, 
				stops.lat, 
				rides.departure_time, 
				stops.stop_name 
			FROM rides 
			INNER JOIN stops ON rides.id_stop = stops.id_stop 
			WHERE rides.id_trip = %s 
			ORDER BY rides.shape_dist_traveled""",
			(id_trip,)
		)

		# creates geojson file of all stops
		stops_geojson = {}
		stops_geojson["type"] = "FeatureCollection"
		stops_geojson["features"] = []

		for stop in stops:
			stops_geojson["features"].append({
				"name": stop[3],
				"departure_time": stop[2].total_seconds(),
				"geometry": {
					"coordinates": [float(stop[0]), float(stop[1])]
				}
			})

		return stops_geojson

	def get_trips_by_stop(self, stop_name, semi_now: datetime = 'now'):

		if semi_now == 'now':
			semi_now = datetime.now()

		# selects trips passing the given stop updated in last 10 minutes
		trips = self.database_connection.execute_fetchall("""
			SELECT 
				trips.trip_source_id, 
				trips.current_delay, 
				headsigns.headsign, 
				trips.trip_no 
			FROM trips 
			JOIN headsigns ON 
				trips.id_headsign = headsigns.id_headsign AND 
				trips.last_updated > %s - interval 10 MINUTE 
				AND id_trip IN (
					SELECT DISTINCT id_trip 
					FROM rides 
					JOIN stops ON 
						rides.id_stop = stops.id_stop AND 
						stops.stop_name = %s);""",
			(semi_now, stop_name))

		# selects departure time for all trips passing the given stop
		stop_times = self.database_connection.execute_fetchall("""
			SELECT 
				trips.trip_source_id, 
				rides.departure_time 
			FROM trips 
			JOIN rides ON 
				trips.id_trip = rides.id_trip AND 
				rides.id_stop IN (
					SELECT id_stop 
					FROM stops 
					WHERE stop_name = %s)""",
			(stop_name,))

		# transforms database result to dict
		# trip_id -> departure time
		stop_time_dict = {}
		for stop_time in stop_times:
			stop_time_dict[stop_time[0]] = stop_time[1]

		trips_json = []
		now = datetime.now()
		sec_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

		for trip in trips:

			# if trip will pass the stop it keeps the trip and add it to return var
			# else it erases the trip
			# scheduled departure < last update time the given trip (is is now)
			# shifted by delay -> it shows delayed buses which should passed the stop already
			if stop_time_dict[trip[0]].seconds < sec_since_midnight - trip[1]:
				continue

			trip_json = {}
			trip_json["id"] = trip[0]
			trip_json["delay"] = trip[1]
			trip_json["headsign"] = trip[2]
			trip_json["trip_no"] = trip[3]
			trip_json["departure_time"] = stop_time_dict[trip[0]].total_seconds()
			trips_json.append(trip_json)

		return trips_json


	def server(self, environ, start_response):

		if environ['REQUEST_METHOD'] == 'GET':
			try:
				request_body = environ['PATH_INFO'][1:str(environ['PATH_INFO']).index('&')]
				response_body = None
				if "vehicles_positions" == request_body:
					response_body = json.dumps(self.get_vehicles_positions())

				# for given trip_id it returns its stops and tail and shape
				elif "trip" == request_body.split('.')[0]:
					trip_id = request_body[request_body.index('.')+1:]
					response_body = '[' + \
						json.dumps(self.get_shape(trip_id)) + ',' + \
						json.dumps(self.get_tail(trip_id)) + ',' + \
						json.dumps(self.get_stops(trip_id)) + ']'

				# returns tail for trip of the given trip_id
				elif "tail" == request_body.split('.')[0]:
					response_body = json.dumps(self.get_tail(
						request_body[request_body.index('.')+1:]))

				# returns shape for trip of the given trip_id
				elif "shape" == request_body.split('.')[0]:
					response_body = json.dumps(self.get_shape(
						request_body[request_body.index('.')+1:]))

				# returns stops for trip of the given trip_id
				elif "stops" == request_body.split('.')[0]:
					response_body = json.dumps(self.get_stops(
						request_body[request_body.index('.')+1:]))

				# returns trip_id for all trips passing the given stop and their timetables
				elif "trips_by_stop" == request_body.split('.')[0]:
					# print(quote(fix_text(request_body[request_body.index('.')+1:])))
					response_body = json.dumps(self.get_trips_by_stop(fix_text(
						request_body[request_body.index('.')+1:])))

					print(response_body)

				# print(response_body)
				status = '200 OK'
				headers = [('Content-type', 'text/plain')]
				start_response(status, headers)
				return [response_body.encode()]
			except (TypeError, ValueError, IndexError):
				logging.warning("invalid request: " + str(environ))
				response_body = "invalid request"
				status = '404'
				headers = [('Content-type', 'text/html'),
						   ('Content-Length', str(len(response_body)))]
				start_response(status, headers)
				return [response_body.encode()]
			except Exception as e:
				logging.warning("Something went wrong: " + str(e))
				response_body = "internal error"
				status = '500'
				headers = [('Content-type', 'text/html'),
						   ('Content-Length', str(len(response_body)))]
				start_response(status, headers)
				return [response_body.encode()]
		else:
			logging.warning("POST method should not occurs.")
			response_body = "bad request"
			status = '400'
			headers = [('Content-type', 'text/html'),
					   ('Content-Length', str(len(response_body)))]
			start_response(status, headers)
			return [response_body.encode()]


	def start_server(self):
		"""Start the server."""
		httpd = make_server("", self.PORT, self.server)
		thread = threading.Thread(target=httpd.serve_forever)
		thread.start()

		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			pass

		httpd.server_close()
		thread.join()
		sys.exit()


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--database", default='vehicle_positions_test_database', type=str,
		help="Says source database name")
	args = parser.parse_args([] if "__file__" not in globals() else None)

	server = Server(args.database)
	server.start_server()