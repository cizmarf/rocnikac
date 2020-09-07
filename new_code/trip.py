import inspect
import json
from datetime import datetime
from functools import wraps
from pathlib import Path

import pytz

from file_system import File_system
from network import Network

class Trip:

	@staticmethod
	def format_shape_traveled(shape_t: str) -> int:
		return int(float(shape_t) * 1000)

	def _initializer(func):
		"""
		decorator who sets all self variables by constructor attributes
		:return: wrapper of function
		:rtype: function
		"""
		all_args = inspect.getfullargspec(func)
		names, varargs, keywords, defaults = all_args[0], all_args[1], all_args[2], all_args[3]

		@wraps(func)
		def wrapper(self, *args, **kargs):
			for name, arg in list(zip(names[1:], args)) + list(kargs.items()):
				setattr(self, name, arg)

			for name, default in zip(reversed(names), reversed(defaults)):
				if not hasattr(self, name):
					setattr(self, name, default)

			func(self, *args, **kargs)

		return wrapper

	# @_initializer
	def __init__(self):
		self.trip_id: str = None
		self.lat: str = None
		self.lon: str = None
		self.last_updated=None
		self.cur_delay: int = None
		self.last_stop_delay = None
		self.shape_traveled: int = None
		self.trip_no: str = None
		self.trip_headsign: str = None
		self.id_trip_headsign: int = None
		self.id_trip: int = None

		self.last_stop = None
		self.next_stop = None
		self.last_stop_shape_dist_trav = None
		self.arrival_time = None
		self.departure_time = None
		self.stop_dist_diff = None

		self.json_trip = None
		self.json_file = None
		
	def set_attributes_by_vehicle(self, vehicle: dict):
		self.json_file = vehicle
		self.trip_id = vehicle["properties"]["trip"]["gtfs_trip_id"]
		self.lat = vehicle["geometry"]["coordinates"][1]
		self.lon = vehicle["geometry"]["coordinates"][0]
		self.cur_delay = int(vehicle["properties"]["last_position"]["delay"])  # TODO rewrite on model delay in use
		self.shape_traveled = Trip.format_shape_traveled(vehicle["properties"]["last_position"]["gtfs_shape_dist_traveled"])
		self.trip_no = vehicle["properties"]["trip"]["gtfs_route_short_name"]
		self.last_stop_delay = vehicle["properties"]["last_position"]["delay_stop_departure"]
		if self.last_stop_delay is None:
			self.last_stop_delay = vehicle["properties"]["last_position"]["delay_stop_arrival"]
		last_updated = vehicle["properties"]["last_position"]["origin_timestamp"]

		# extracts time from json and sets timezone to UTC and convert the time to prague timezone
		self.last_updated = pytz.utc.localize(datetime.strptime(last_updated[:last_updated.index(".")], '%Y-%m-%dT%H:%M:%S')).astimezone(pytz.timezone('Europe/Prague'))
		self.id_trip = None

	# deprecated
	def to_real_time_geojson(self, database_connection) -> dict:
		headsign = database_connection.execute_fetchall('SELECT headsigns.headsign, current_delay FROM headsigns JOIN trips ON trips.id_headsign = headsigns.id_headsign AND id_trip = %s', (self.id_trip,))
		if len(headsign) != 0:
			self.trip_headsign = headsign[0][0]
			self.cur_delay = headsign[0][1]
		else:
			self.trip_headsign = "No data"

		bus_output_list = {}
		bus_output_list["type"] = "Feature"
		bus_output_list["properties"] = {}
		bus_output_list["properties"]["gtfs_trip_id"] = self.trip_id
		bus_output_list["properties"]["gtfs_route_short_name"] = self.trip_no
		bus_output_list["properties"]["headsign"] = self.trip_headsign
		bus_output_list["properties"]["delay"] = self.cur_delay
		bus_output_list["geometry"] = {}
		bus_output_list["geometry"]["coordinates"] = [self.lon, self.lat]
		bus_output_list["geometry"]["type"] = "Point"
		return bus_output_list


	# self.id_trip = id_trip
	# self.id_trip_headsign = id_trip_headsign
	# self.trip_no = trip_no
	# self.shape_traveled = shape_traveled
	# self.cur_delay = cur_delay
	# self.lon = lon
	# self.lat = lat
	# self.trip_id = trip_id
	# self.trip_headsign = trip_headsign
	# self.last_stop_delay = last_stop_delay


	def get_tuple_new_trip(self, static: bool) -> tuple:
		if static:
			timezone = pytz.timezone("Europe/Prague")
			now = timezone.localize(datetime.now().replace(microsecond=0))

			return (self.trip_id, self.trip_headsign, self.cur_delay, self.shape_traveled, self.trip_no, now, self.lat, self.lon)
		else:
			return (self.trip_id, self.trip_headsign, self.cur_delay, self.shape_traveled, self.trip_no, self.last_updated, self.lat, self.lon)

	def get_tuple_update_trip(self, static) -> tuple:
		if static:
			timezone = pytz.timezone("Europe/Prague")
			now = timezone.localize(datetime.now().replace(microsecond=0))

			return (self.trip_id, self.cur_delay, self.last_stop_delay, self.shape_traveled, self.lat, self.lon, now)
		else:
			return (self.trip_id, self.cur_delay, self.last_stop_delay, self.shape_traveled, self.lat, self.lon, self.last_updated)

	def get_tuple_for_predict(self):
		try:
			return (self.shape_traveled - self.last_stop_shape_dist_trav, self.last_updated, self.departure_time, self.arrival_time)
		except Exception as e:
			return None

	async def get_async_json_trip_file(self):
		self.json_trip = await Network.download_async_URL_to_json(Network.trip_by_id(self.trip_id))
		self._fill_attributes_from_trip_file()

	def static_get_json_trip_file(self):
		content = File_system.get_tar_file_content((File_system.static_trips / self.trip_id).with_suffix(".tar.gz"))
		self.json_trip = json.loads(content)
		self._fill_attributes_from_trip_file()

	def save_shape_file(self, path=File_system.all_shapes):
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
		for feature in self.json_trip["shapes"]:
			new_json_data["features"][0]["geometry"]["coordinates"].append(feature["geometry"]["coordinates"])
			new_json_data["features"][0]["geometry"]["properties"]["shape_dist_traveled"].append(
				Trip.format_shape_traveled(feature["properties"]["shape_dist_traveled"]))

		File_system.save_file(new_json_data, (Path(path) / self.trip_id).with_suffix('.shape'))
			
	def _fill_attributes_from_trip_file(self):
		self.trip_headsign = self.json_trip["trip_headsign"]

