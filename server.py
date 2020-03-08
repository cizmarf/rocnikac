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

from common_functions import allFilesURL, Log, GI
from common_functions import SQL_queries


class Veh_pos_file_handler(FileSystemEventHandler):

	def on_modified(self, event):
		if event is not None and event.src_path == str(allFilesURL.vehicles_positions) or event is None:
			try:
				with open(allFilesURL.vehicles_positions, 'r') as f:
					if f.mode == 'r':
						self.veh_pos_file_content = f.read()
			except IOError as e:
				logging.warning("IOE " + e)

	def __init__(self):
		self.veh_pos_file_content = ""
		self.on_modified(None)


class Database_connection:
	def __init__(self):
		self.connection_db = mysql.connector.connect(
			host="localhost",
			database="vehicles_info",
			user="vehicles_access",
			passwd="my_password",
			autocommit=True
		)
		self.cursor_prepared_db = self.connection_db.cursor(prepared=True)
		self.cursor_db = self.connection_db.cursor()
		self.trip_id_to_id_trip_map = {}

		SQL_queries.sql_run_transaction(
			self.connection_db,
			self.cursor_db,
			'SET @@session.time_zone = "+00:00"'
		)

	def get_id_trip_by_trip_id(self, trip_id):
		# print("trip_id from connection:", trip_id)
		if trip_id in self.trip_id_to_id_trip_map:
			return self.trip_id_to_id_trip_map[trip_id]
		else:
			try:
				id_trip =  SQL_queries.sql_get_result(
					self.cursor_db,
					'SELECT id_trip FROM trips WHERE trip_id = %s LIMIT 1',
					(trip_id,)
				)[0][0]
				self.trip_id_to_id_trip_map[trip_id] = id_trip
				return id_trip
			except IndexError:
				logging.error("Trip", trip_id, "is not in database.")


def prepare_geojson_lfms():
	geojson_lfms = {}
	geojson_lfms[GI.type] = GI.featureCollection
	geojson_lfms[GI.features] = [{}]
	geojson_lfms[GI.features][0][GI.type] = GI.feature
	geojson_lfms[GI.features][0][GI.properties] = {}
	geojson_lfms[GI.features][0][GI.geometry] = {}
	geojson_lfms[GI.features][0][GI.geometry][GI.type] = GI.lineString
	geojson_lfms[GI.features][0][GI.geometry][GI.coordinates] = []
	return geojson_lfms

#TODO file buffer

def get_lfms(trip_id):
	with open((allFilesURL.trips_shapes / trip_id).with_suffix(".shape"), "r") as f:
		shape = json.loads(f.read())

		# print("trip_id from get lfsm:", trip_id)

		id_trip = connection.get_id_trip_by_trip_id(trip_id)

		# print("id_trip", id_trip)

		coordinates = SQL_queries.sql_get_result(
			connection.cursor_db,
			'SELECT lon, lat, shape_traveled FROM trip_coordinates WHERE trip_coordinates.id_trip = %s AND trip_coordinates.time > DATE_SUB(NOW(), INTERVAL 5 MINUTE) ORDER BY trip_coordinates.time',
			(id_trip,)
		)

		geojson_lfms = prepare_geojson_lfms()
		if len(coordinates) > 0:
			geojson_lfms[GI.features][0][GI.geometry][GI.coordinates].append([float(coordinates[0][0]), float(coordinates[0][1])])

			for i in range(len(shape[GI.features][0][GI.geometry][GI.coordinates])):
				shape_fault = shape[GI.features][0][GI.geometry][GI.coordinates][i]
				shape_dist_traveled = shape["features"][0]["geometry"]["properties"]["shape_dist_traveled"][i]

				if float(coordinates[0][2]) < float(shape_dist_traveled) < float(coordinates[-1][2]):
					geojson_lfms[GI.features][0][GI.geometry][GI.coordinates].append(shape_fault)

			geojson_lfms[GI.features][0][GI.geometry][GI.coordinates].append([float(coordinates[-1][0]), float(coordinates[-1][1])])

		return geojson_lfms


def get_shape(trip_id):
	with open((allFilesURL.trips_shapes / trip_id).with_suffix(".shape"), "r") as f:
		# print("Shape opened")
		shape = json.loads(f.read())
		shape["features"][0]["geometry"]["properties"] = {}
		shape["features"][0]["properties"] = {}
		# print("shape:", shape)
		return shape

def get_stops(trip_id):
	id_trip = connection.get_id_trip_by_trip_id(trip_id)
	stops = SQL_queries.sql_get_result(
		connection.cursor_db,
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



FILE = 'index.html'
PORT = 8080


def server(environ, start_response):

	if environ['REQUEST_METHOD'] == 'POST':
		try:
			request_body_size = int(environ['CONTENT_LENGTH'])
			request_body = environ['wsgi.input'].read(request_body_size)
		except (TypeError, ValueError):
			request_body = None

		response_body = ""
		request_body = request_body.decode('utf-8')
		print("any request")
		if "vehicles_positions" == request_body:
			response_body = event_handler.veh_pos_file_content
			print("veh")
			print(response_body)

		elif "lfms" == request_body.split('.')[0]:
			# print("rb:", request_body)
			response_body = json.dumps(get_lfms(request_body.split('.')[1]))

		elif "shape" == request_body.split('.')[0]:
			response_body = json.dumps(get_shape(request_body.split('.')[1]))

		elif "stops" == request_body.split('.')[0]:
			response_body = json.dumps(get_stops(request_body.split('.')[1]))

		status = '200 OK'
		headers = [('Content-type', 'text/plain')]
		start_response(status, headers)
		return [response_body.encode()]
	else:
		logging.warning("GET method should not occurs.")
		response_body = open(FILE).read()
		status = '400'
		headers = [('Content-type', 'text/html'),
				   ('Content-Length', str(len(response_body)))]
		start_response(status, headers)
		return [response_body.encode()]


def start_server():
	"""Start the server."""
	httpd = make_server("", PORT, server)

	global event_handler
	event_handler = Veh_pos_file_handler()
	observer = Observer()
	observer.schedule(event_handler, path=str(allFilesURL.prefix / allFilesURL.data), recursive=False)
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
	logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=allFilesURL.log_server, filemode='w')
	logging.info(Log.start)
	connection = Database_connection()
	start_server()


