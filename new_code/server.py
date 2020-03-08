import argparse
import datetime
import json
import logging
import sys
import threading
import time
import webbrowser
from pathlib import Path
from wsgiref.simple_server import make_server

import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from new_code.database import Database
from new_code.file_system import File_system

class Server:

	class Veh_pos_file_handler(FileSystemEventHandler):

		def on_modified(self, event):
			if event is not None and event.src_path == str(File_system.all_vehicle_positions_real_time_geojson) or event is None:
				try:
					with open(File_system.all_vehicle_positions_real_time_geojson, 'r') as f:
						if f.mode == 'r':
							self.veh_pos_file_content = f.read()
				except IOError as e:
					logging.warning("IOE " + e)

		def __init__(self):
			self.veh_pos_file_content = ""
			self.on_modified(None)

	def __init__(self):
		self.database_connection = Database()
		self.trip_id_to_id_trip_map = {}
		self.FILE = 'index.html'
		self.PORT = 8080

	def get_id_trip_by_trip_id(self, trip_id):
		# print("trip_id from connection:", trip_id)
		if trip_id in self.trip_id_to_id_trip_map:
			return self.trip_id_to_id_trip_map[trip_id]
		else:
			try:
				id_trip = self.database_connection.execute_fetchall(
					'SELECT id_trip FROM trips WHERE trip_id = %s LIMIT 1',
					(trip_id,)
				)[0][0]
				self.trip_id_to_id_trip_map[trip_id] = id_trip
				return id_trip
			except IndexError:
				logging.error("Trip", trip_id, "is not in database.")


	def prepare_geojson_tail(self):
		geojson_tail = {}
		geojson_tail["type"] = "FeatureCollection"
		geojson_tail["features"] = [{}]
		geojson_tail["features"][0]["type"] = "feature"
		geojson_tail["features"][0]["properties"] = {}
		geojson_tail["features"][0]["geometry"] = {}
		geojson_tail["features"][0]["geometry"]["type"] = "LineString"
		geojson_tail["features"][0]["geometry"]["coordinates"] = []
		return geojson_tail

	#TODO file buffer

	def get_tail(self, trip_id):
		with open((File_system.all_shapes / trip_id).with_suffix(".shape"), "r") as f:
			shape = json.loads(f.read())

			# print("trip_id from get lfsm:", trip_id)

			id_trip = self.get_id_trip_by_trip_id(trip_id)

			# print("id_trip", id_trip)

			coordinates = self.database_connection.execute_fetchall(
				'SELECT lon, lat, shape_traveled FROM trip_coordinates WHERE trip_coordinates.id_trip = %s AND trip_coordinates.time > DATE_SUB(NOW(), INTERVAL 5 MINUTE) ORDER BY trip_coordinates.time',
				(id_trip,)
			)

			geojson_tail = self.prepare_geojson_tail()
			if len(coordinates) > 0:
				geojson_tail["features"][0]["geometry"]["coordinates"].append([float(coordinates[0][0]), float(coordinates[0][1])])

				for i in range(len(shape["features"][0]["geometry"]["coordinates"])):
					shape_fault = shape["features"][0]["geometry"]["coordinates"][i]
					shape_dist_traveled = shape["features"][0]["geometry"]["properties"]["shape_dist_traveled"][i]

					if float(coordinates[0][2]) < float(shape_dist_traveled) < float(coordinates[-1][2]):
						geojson_tail["features"][0]["geometry"]["coordinates"].append(shape_fault)

				geojson_tail["features"][0]["geometry"]["coordinates"].append([float(coordinates[-1][0]), float(coordinates[-1][1])])

			return geojson_tail


	def get_shape(self, trip_id):
		with open((File_system.all_shapes / trip_id).with_suffix(".shape"), "r") as f:
			# print("Shape opened")
			shape = json.loads(f.read())
			shape["features"][0]["geometry"]["properties"] = {}
			shape["features"][0]["properties"] = {}
			# print("shape:", shape)
			return shape

	def get_stops(self, trip_id):
		id_trip = self.get_id_trip_by_trip_id(trip_id)
		stops = self.database_connection.execute_fetchall(
			'SELECT stops.lon, stops.lat, rides.departure_time, stops.stop_name fROM rides INNER JOIN stops ON rides.id_stop = stops.id_stop WHERE rides.id_trip = %s ORDER BY rides.shape_dist_traveled',
			(id_trip,)
		)

		print("stops:", stops)

		stops_geojson = {}
		stops_geojson["type"] = "FeatureCollection"
		stops_geojson["features"] = []
		for stop in stops:
			stops_geojson["features"].append({"name": stop[3], "geometry": {"coordinates": [float(stop[0]), float(stop[1])]}})

		print("stops_goej:", stops_geojson)
		return stops_geojson


	def server(self, environ, start_response):

		if environ['REQUEST_METHOD'] == 'POST':
			try:
				request_body_size = int(environ['CONTENT_LENGTH'])
				request_body = environ['wsgi.input'].read(request_body_size)
			except (TypeError, ValueError):
				request_body = None

			response_body = ""
			request_body = request_body.decode('utf-8')
			if "vehicles_positions" == request_body:
				print("veh_pos")
				response_body = event_handler.veh_pos_file_content

			elif "tail" == request_body.split('.')[0]:
				# print("rb:", request_body)
				response_body = json.dumps(self.get_tail(request_body.split('.')[1]))

			elif "shape" == request_body.split('.')[0]:
				response_body = json.dumps(self.get_shape(request_body.split('.')[1]))

			elif "stops" == request_body.split('.')[0]:
				response_body = json.dumps(self.get_stops(request_body.split('.')[1]))

			status = '200 OK'
			headers = [('Content-type', 'text/plain')]
			start_response(status, headers)
			return [response_body.encode()]
		else:
			logging.warning("GET method should not occurs.")
			response_body = open(self.FILE).read()
			status = '400'
			headers = [('Content-type', 'text/html'),
					   ('Content-Length', str(len(response_body)))]
			start_response(status, headers)
			return [response_body.encode()]


	def start_server(self):
		"""Start the server."""
		httpd = make_server("", self.PORT, self.server)

		global event_handler
		event_handler = Server.Veh_pos_file_handler()
		observer = Observer()
		observer.schedule(event_handler, path=str(File_system.all_shapes), recursive=False)
		observer.start()

		thread = threading.Thread(target=httpd.serve_forever)
		thread.start()

		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			observer.stop()

		observer.join()
		thread.join()
		sys.exit()


if __name__ == "__main__":
	# logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=allFilesURL.log_server, filemode='w')
	# logging.info(Log.start)
	server = Server()
	server.start_server()


