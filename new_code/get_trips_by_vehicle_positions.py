import json
from io import BytesIO
from os.path import getmtime
import glob
import tarfile

from new_code.file_system import File_system
from new_code.network import Network
from new_code.all_vehicle_positions import All_vehicle_positions
from new_code.trip import Trip


files = glob.glob(File_system.static_vehicle_positions + "*.tar.gz")
files.sort(key=getmtime)

not_found_trips = set()
found_trips = set()

for file in files:
	content = File_system.get_tar_file_content(file)

	all_vehicle_positions = All_vehicle_positions()

	all_vehicle_positions.json_file = json.loads(content)

	for vehicle in all_vehicle_positions.iterate_vehicles():

		if vehicle.trip_id in not_found_trips or vehicle.trip_id in found_trips:
			continue

		try:
			vehicle.get_json_trip_file()

			File_system.save_tar_file(vehicle.json_trip, File_system.static_trips + str(vehicle.trip_id) + ".tar.gz", str(vehicle.trip_id) + ".json")

			found_trips.add(vehicle.trip_id)

			print("trip saved:", vehicle.trip_id)

		except IOError as e:
			print("getting " + vehicle.trip_id + "failed")
			not_found_trips.add(vehicle.trip_id)
			continue


