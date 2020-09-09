import json
import unittest
from datetime import datetime

from file_system import File_system
from trip import Trip


class TestTrip(unittest.TestCase):
	def test_format_shape_traveled(self):
		self.assertEqual(Trip.format_shape_traveled(str(20)), 20000)

	def test_set_attributes_by_vehicle(self):
		json_file = json.loads(File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz"))
		trip = Trip()
		trip.set_attributes_by_vehicle(json_file["features"][3])

		self.assertEqual(trip.cur_delay, 82)
		self.assertEqual(trip.json_file, json_file["features"][3])
		self.assertEqual(trip.last_stop_delay, 82)
		self.assertEqual(str(trip.last_updated), "2020-02-20 14:49:42+01:00")
		self.assertEqual(trip.lat, 50.24123)
		self.assertEqual(trip.lon, 13.79784)
		self.assertEqual(trip.shape_traveled, 41400)
		self.assertEqual(trip.trip_id, '619_16_200106')
		self.assertEqual(trip.trip_no, '619')

	# get_async_json_trip_file and static_get_json_trip_file methods are tested in network test or filesystem test and integration tests

	def	test_save_shape_file(self):
		from trip import Trip

		json_file = json.loads(File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz"))

		for vehicle in json_file["features"]:
			if vehicle["properties"]["trip"]["gtfs_trip_id"] == "421_225_191114":
				trip = Trip()
				trip.set_attributes_by_vehicle(vehicle)
				trip.json_trip = json.loads(File_system.get_file_content("../input_data/421_225_191114.json"))
				trip._fill_attributes_from_trip_file()
				trip.save_shape_file('../output_data/')
				break

		shape_json = json.loads(File_system.get_file_content('../output_data/421_225_191114.shape'))
		File_system.delete_file('../output_data/421_225_191114.shape')

		shape_dist_trav = shape_json['features'][0]['geometry']['properties']['shape_dist_traveled']
		coordinates = shape_json['features'][0]['geometry']['coordinates']

		self.assertIsInstance(shape_dist_trav, list)
		self.assertIsInstance(coordinates, list)
		self.assertEqual(len(shape_dist_trav), len(coordinates))
		self.assertEqual(len(shape_dist_trav), 1198)
		self.assertEqual(shape_dist_trav[1], 17)

	def test_get_tuple_new_trip(self):
		json_file = json.loads(File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz"))

		for vehicle in json_file["features"]:
			if vehicle["properties"]["trip"]["gtfs_trip_id"] == "421_225_191114":
				trip = Trip()
				trip.set_attributes_by_vehicle(vehicle)
				trip.json_trip = json.loads(File_system.get_file_content("../input_data/421_225_191114.json"))
				trip._fill_attributes_from_trip_file()

				static_tuple_trip = trip.get_tuple_new_trip(True)
				real_tuple_trip = trip.get_tuple_new_trip(False)

				self.assertEqual(static_tuple_trip[0], '421_225_191114')
				self.assertEqual(static_tuple_trip[1], 'Kolín,Nádraží')
				self.assertEqual(static_tuple_trip[2], 37)
				self.assertEqual(static_tuple_trip[3], 37)
				self.assertEqual(static_tuple_trip[4], 22300)
				self.assertEqual(static_tuple_trip[5], '421')
				# test time now
				self.assertEqual(static_tuple_trip[7], 49.93896)
				self.assertEqual(static_tuple_trip[8], 14.98064)

				self.assertEqual(real_tuple_trip[0], '421_225_191114')
				self.assertEqual(real_tuple_trip[1], 'Kolín,Nádraží')
				self.assertEqual(real_tuple_trip[2], 37)
				self.assertEqual(real_tuple_trip[3], 37)
				self.assertEqual(real_tuple_trip[4], 22300)
				self.assertEqual(real_tuple_trip[5], '421')
				self.assertEqual(str(real_tuple_trip[6]), '2020-02-20 14:49:20+01:00')
				self.assertEqual(real_tuple_trip[7], 49.93896)
				self.assertEqual(real_tuple_trip[8], 14.98064)

				break

	def test_get_tuple_update_trip(self):
		json_file = json.loads(File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz"))

		trip = Trip()
		trip.set_attributes_by_vehicle(json_file["features"][0])

		static_tuple_trip = trip.get_tuple_update_trip(True)
		real_tuple_trip = trip.get_tuple_update_trip(False)

		self.assertEqual(static_tuple_trip[0], '381_72_191128')
		self.assertEqual(static_tuple_trip[1], 142)
		self.assertEqual(static_tuple_trip[2], 142)
		self.assertEqual(static_tuple_trip[3], 53100)
		self.assertEqual(static_tuple_trip[4], 50.03094)
		self.assertEqual(static_tuple_trip[5], 14.60711)
		# test time now

		self.assertEqual(real_tuple_trip[0], '381_72_191128')
		self.assertEqual(real_tuple_trip[1], 142)
		self.assertEqual(real_tuple_trip[2], 142)
		self.assertEqual(real_tuple_trip[3], 53100)
		self.assertEqual(real_tuple_trip[4], 50.03094)
		self.assertEqual(real_tuple_trip[5], 14.60711)
		self.assertEqual(str(real_tuple_trip[6]), '2020-02-20 14:49:37+01:00')

	def test_get_tuple_for_predict(self):
		trip = Trip()
		trip.shape_traveled = 1000
		trip.last_stop_shape_dist_trav = 100
		trip.last_updated = 'upd'
		trip.departure_time = 'dep'
		trip.arrival_time = 'arr'

		trip_tuple = trip.get_tuple_for_predict()

		self.assertEqual(trip_tuple[0], 900)
		self.assertEqual(trip_tuple[1], 'upd')
		self.assertEqual(trip_tuple[2], 'dep')
		self.assertEqual(trip_tuple[3], 'arr')

if __name__ == '__main__':
	unittest.main()
