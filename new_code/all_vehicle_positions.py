import glob
import json
import time
from os.path import getmtime

from file_system import File_system
from network import Network
from trip import Trip

class Static_all_vehicle_positions:

	def __init__(self):
		# path = str(File_system.static_vehicle_positions) + "*.tar.gz"
		self.files = glob.glob(str(File_system.static_vehicle_positions) + "/*.tar.gz")
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
				trip.set_attributes_by_vehicle(vehicle)
				self.vehicles.append(trip)
		except KeyError:
			print("error")

	def get_trip_source_id_by_vehicle(self, vehicle) -> str:
		return vehicle.trip_id

	def estimate_delays(self):


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