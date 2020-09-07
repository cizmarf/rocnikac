import unittest
import datetime

from network import Network

class MyTestCase(unittest.TestCase):

	def test_format_vehicle_positions_file(self):
		file_json = Network.download_URL_to_json(Network.vehicles_positions)

		# if the following test fail something is wrong with Golemio API
		self.assertIn('features', file_json)
		self.assertIn('geometry', file_json['features'][0])
		self.assertIn('properties', file_json['features'][0])

		from trip import Trip

		trip = Trip()
		trip.set_attributes_by_vehicle(file_json["features"][0])

		self.assertIsInstance(trip.cur_delay, int)
		self.assertIsInstance(trip.json_file, dict)
		self.assertIsInstance(trip.last_stop_delay, int)
		self.assertIsInstance(trip.last_updated, datetime.datetime)
		self.assertIsInstance(trip.lat, float)
		self.assertIsInstance(trip.lon, float)
		self.assertIsInstance(trip.shape_traveled, int)
		self.assertIsInstance(trip.trip_id, str)
		self.assertIsInstance(trip.trip_no, str)


if __name__ == '__main__':
	unittest.main()
