import unittest
from datetime import timedelta

import tests.lib_tests
from all_vehicle_positions import *
from database import Database


class testStatic_all_vehicle_positions(unittest.TestCase):
	def test_init(self):
		savp = Static_all_vehicle_positions()
		self.assertGreater(len(savp.files), 10000)

	def test_static_get_all_vehicle_positions_json(self):
		savp = Static_all_vehicle_positions()
		for file in savp.static_get_all_vehicle_positions_json():
			self.assertIsInstance(file, dict)
			break


class testAll_vehicle_positions(unittest.TestCase):
	def test_findFirstOccurrence(self):
		input_list_a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
		input_list_b = [0, 1, 2, 3, 4, 4, 4, 7, 8, 9, 10]
		input_list_c = [0, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

		self.assertEqual(All_vehicle_positions.findFirstOccurrence(input_list_a, 7), 7)
		self.assertEqual(All_vehicle_positions.findFirstOccurrence(input_list_b, 4), 4)
		self.assertEqual(All_vehicle_positions.findFirstOccurrence(input_list_c, 1), 1)

		rev = input_list_a[::-1]

		self.assertEqual(All_vehicle_positions.findFirstOccurrence(input_list_a[::-1], 7), 3)

	def test_get_sublist(self):
		input_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

		self.assertListEqual(All_vehicle_positions.get_sublist(input_list, 2, 4), [2, 3])

	def test_construct_all_trips(self):
		tests.lib_tests.drop_all_tables()
		args = tests.lib_tests.get_args()
		database_connection = Database("vehicle_positions_test_database")

		import download_and_process

		vehicle_positions = All_vehicle_positions()
		vehicle_positions.json_file = json.loads(File_system.get_file_content("../input_data/2020-02-20T13.50.23_3_trips.json"))
		vehicle_positions.construct_all_trips(database_connection)

		first_insert_true = File_system.pickle_load_object("../output_data/test_construct_all_trips_vehicles_1.list")
		first_insert_result = vehicle_positions.vehicles

		# File_system.pickle_object(first_insert_result, "../output_data/test_construct_all_trips_vehicles_1.list")
		
		self.assertEqual(len(first_insert_true), len(first_insert_result))
		
		first_insert_true = first_insert_true[0]
		first_insert_result = first_insert_result[0]

		download_and_process.asyncio.run(download_and_process.process_async_vehicles(vehicle_positions, database_connection, args))

		vehicle_positions = All_vehicle_positions()
		vehicle_positions.json_file = json.loads(File_system.get_file_content("../input_data/2020-02-20T13.50.23_3_trips.json"))
		vehicle_positions.construct_all_trips(database_connection)

		second_insert_true = File_system.pickle_load_object("../output_data/test_construct_all_trips_vehicles_2.list")
		second_insert_result = vehicle_positions.vehicles

		# File_system.pickle_object(second_insert_result, "../output_data/test_construct_all_trips_vehicles_2.list")

		self.assertEqual(len(second_insert_true), len(second_insert_result))

		second_insert_true = second_insert_true[0]
		second_insert_result = second_insert_result[0]

		self.assertEqual(first_insert_true.cur_delay, first_insert_result.cur_delay)
		self.assertDictEqual(first_insert_true.json_file, first_insert_result.json_file)
		self.assertEqual(first_insert_true.last_stop_delay, first_insert_result.last_stop_delay)
		self.assertEqual(first_insert_true.last_updated, first_insert_result.last_updated)
		self.assertEqual(first_insert_true.lat, first_insert_result.lat)
		self.assertEqual(first_insert_true.lon, first_insert_result.lon)
		self.assertEqual(first_insert_true.shape_traveled, first_insert_result.shape_traveled)
		self.assertEqual(first_insert_true.trip_id, first_insert_result.trip_id)
		self.assertEqual(first_insert_true.trip_no, first_insert_result.trip_no)

		self.assertEqual(second_insert_true.cur_delay, second_insert_result.cur_delay)
		self.assertDictEqual(second_insert_true.json_file, second_insert_result.json_file)
		self.assertEqual(second_insert_true.last_stop_delay, second_insert_result.last_stop_delay)
		self.assertEqual(second_insert_true.last_updated, second_insert_result.last_updated)
		self.assertEqual(second_insert_true.lat, second_insert_result.lat)
		self.assertEqual(second_insert_true.lon, second_insert_result.lon)
		self.assertEqual(second_insert_true.shape_traveled, second_insert_result.shape_traveled)
		self.assertEqual(second_insert_true.trip_headsign, second_insert_result.trip_headsign)
		self.assertEqual(second_insert_true.trip_id, second_insert_result.trip_id)
		self.assertEqual(second_insert_true.trip_no, second_insert_result.trip_no)
		self.assertEqual(second_insert_true.last_stop, second_insert_result.last_stop)
		self.assertEqual(second_insert_true.next_stop, second_insert_result.next_stop)
		self.assertEqual(second_insert_true.last_stop_shape_dist_trav, second_insert_result.last_stop_shape_dist_trav)
		self.assertEqual(second_insert_true.departure_time, second_insert_result.departure_time)
		self.assertEqual(second_insert_true.arrival_time, second_insert_result.arrival_time)
		self.assertEqual(second_insert_true.stop_dist_diff, second_insert_result.stop_dist_diff)

	def test_get_trip_rides_sublist(self):
		trip_rides = File_system.pickle_load_object('../input_data/get_last_next_stop_and_sdt_trip_rides.list')

		trip_ids = list(zip(*trip_rides))[0]

		trip_ride_a = All_vehicle_positions.get_trip_rides_sublist(trip_rides, trip_ids, '317_236_191125')
		trip_ride_b = All_vehicle_positions.get_trip_rides_sublist(trip_rides, trip_ids, '381_72_191128')
		trip_ride_c = All_vehicle_positions.get_trip_rides_sublist(trip_rides, trip_ids, '630_189_200210')

		self.assertListEqual(trip_ride_a, trip_rides[0:45])
		self.assertListEqual(trip_ride_b, trip_rides[45:88])
		self.assertListEqual(trip_ride_c, trip_rides[88:124])

	def test_get_last_next_stop_and_sdt(self):
		trip_rides = File_system.pickle_load_object('../input_data/get_last_next_stop_and_sdt_trip_rides.list')

		trip_ids = list(zip(*trip_rides))[0]

		trip_ride_a = All_vehicle_positions.get_trip_rides_sublist(trip_rides, trip_ids, '317_236_191125')

		# trip has just started
		self.assertTupleEqual(All_vehicle_positions.get_last_next_stop_and_sdt(trip_ride_a, 200), (80, 81, 0, timedelta(hours=13, minutes=30, seconds=00), timedelta(hours=13, minutes=32, seconds=00), 1259))

		# trip has not started yet
		self.assertTupleEqual(All_vehicle_positions.get_last_next_stop_and_sdt(trip_ride_a, 0), (80, 81, 0, timedelta(hours=13, minutes=30, seconds=00), timedelta(hours=13, minutes=32, seconds=00), 1259))

		# trip has just arrived first stop
		self.assertTupleEqual(All_vehicle_positions.get_last_next_stop_and_sdt(trip_ride_a, 1259), (81, 82, 1259, timedelta(hours=13, minutes=32, seconds=00), timedelta(hours=13, minutes=38, seconds=00), 5867))

		# on the road
		self.assertTupleEqual(All_vehicle_positions.get_last_next_stop_and_sdt(trip_ride_a, 8000), (82, 83, 7126, timedelta(hours=13, minutes=38, seconds=00), timedelta(hours=13, minutes=40, seconds=00), 1172))

		# trip has just finished its ride
		self.assertTupleEqual(All_vehicle_positions.get_last_next_stop_and_sdt(trip_ride_a, 64016), (None, None, None, None, None, None))

		# trip passed last stop
		self.assertTupleEqual(All_vehicle_positions.get_last_next_stop_and_sdt(trip_ride_a, 70000), (None, None, None, None, None, None))

if __name__ == '__main__':
	unittest.main()
