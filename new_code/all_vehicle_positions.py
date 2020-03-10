import glob
import json
import time
from os.path import getmtime

from new_code.file_system import File_system
from new_code.network import Network
from new_code.trip import Trip

class Static_all_vehicle_positions:

	def __init__(self):
		self.files = glob.glob(str(File_system.static_vehicle_positions.with_suffix("*.tar.gz")))
		self.files.sort(key=getmtime)

	def static_get_all_vehicle_positions_json(self):

		for file in self.files:
			content = File_system.get_tar_file_content(file)

			json_file = json.loads(content)
			yield json_file



class All_vehicle_positions():

	def __init__(self):
		self.json_file = dict()
		self.vehicles = list()


	def iterate_vehicles(self):
		try:
			for vehicle in self.vehicles:
				yield vehicle
		except KeyError as e:
			print("no feature")
			return None


	def get_all_vehicle_positions_json(self):
		self.json_file = Network.download_URL_to_json(Network.vehicles_positions)
		
	def construct_all_trips(self):
		try:
			for vehicle in self.json_file["features"]:
				trip = Trip()
				trip.set_atribudes_by_vehicle(vehicle)
				self.vehicles.append(trip)
		except KeyError:
			print("error")

	def get_trip_source_id_by_vehicle(self, vehicle) -> str:
		return vehicle.trip_id

	def update_geojson_file(self, database_connection):
		geojson_vehiclepositions = {}
		geojson_vehiclepositions["type"] = "FeatureCollection"
		geojson_vehiclepositions["timestamp"] = time.strftime("%Y-%m-%d-%H:%M:%S")
		geojson_vehiclepositions["features"] = []

		try:
			for vehicle in self.vehicles:
				geojson_vehiclepositions["features"].append(vehicle.to_real_time_geojson(database_connection))
		except KeyError as e:
			print("error")
			
		File_system.save_file(geojson_vehiclepositions, File_system.all_vehicle_positions_real_time_geojson)
		


if __name__ == "__main__":
	trip = Trip(
		trip_id=1,
		lat=1,
		lon=1,
		cur_delay=1,
		shape_traveled=2,
		trip_no=3,
		last_stop_delay=4,
		last_updated="56.87"
	)