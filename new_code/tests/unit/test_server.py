import asyncio
import unittest
from random import random
from time import sleep

import numpy as np
import matplotlib.pyplot as plt
import aiohttp
import requests
from pathlib import Path

from server import *

################################################################
# IMPORTANT test server needs fill database by simple static data
# otherwise no test passes
# run testInsertData first and than test server
################################################################

class TestServer(unittest.TestCase):
	def test_get_id_trip_by_trip_id(self):
		server = Server('vehicle_positions_test_database')

		# needs database
		self.assertEqual(1, server.get_id_trip_by_trip_id('467_252_200105'))

		server.database_connection = None

		# should use catch map
		self.assertEqual(1, server.get_id_trip_by_trip_id('467_252_200105'))

	def test_prepare_geojson_tail(self):
		server = Server()

		tail_sample = server.prepare_geojson_tail()

		self.assertIsInstance(tail_sample, dict)
		self.assertDictEqual({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString', 'coordinates': []}}]},
							 tail_sample)

	def test_get_tail(self):
		server = Server('vehicle_positions_test_database')

		tail = server.get_tail('381_49_191201', datetime(2020, 2, 23, 21, 59, 28))

		self.assertIsInstance(tail, dict)
		self.assertEqual({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString', 'coordinates': [
				[14.56198, 50.03388], [14.55963, 50.03324], [14.55935, 50.03317], [14.55421, 50.03184], [14.55321, 50.03154], [14.55116, 50.03125], [14.55028, 50.03127], [14.54927, 50.03145], [14.54787, 50.03188], [14.54485, 50.03313], [14.54385, 50.03337], [14.54228, 50.03336], [14.54149, 50.03333],
				[14.54002, 50.03337], [14.53917, 50.03352], [14.53788, 50.03383], [14.5377, 50.03389], [14.53768, 50.034], [14.5375, 50.03405], [14.53736, 50.03398], [14.53736, 50.03388], [14.53731, 50.0338], [14.53721, 50.03366], [14.53631, 50.03334], [14.53578, 50.0331], [14.53532, 50.03284], [14.53376, 50.03177],
				[14.53342, 50.03154], [14.53319, 50.03142], [14.53278, 50.03123], [14.53216, 50.03109], [14.52845, 50.03067], [14.52803, 50.0306], [14.52721, 50.03048]]}}]},
			tail)

	def test_get_shape(self):
		server = Server('vehicle_positions_test_database')

		from_server = server.get_shape('381_49_191201')
		from_file_system = json.loads(File_system.get_file_content(File_system.all_shapes / Path('381_49_191201').with_suffix('.shape')))

		self.assertIsInstance(from_server, dict)
		self.assertListEqual(from_file_system['features'][0]['geometry']['coordinates'], from_server['features'][0]['geometry']['coordinates'])

	def test_get_stops(self):
		server = Server('vehicle_positions_test_database')

		stops = server.get_stops('467_252_200105')

		self.assertIsInstance(stops, dict)
		self.assertEqual(31, len(stops['features']))
		self.assertEqual('Roudnice n.L.,Purkyňovo nám.', stops['features'][0]['name'])

	def test_get_trips_by_stop(self):
		server = Server('vehicle_positions_test_database')

		trips = server.get_trips_by_stop('Kladno,Nám.Svobody', datetime(2020, 2, 23, 22, 9, 35))

		self.assertIsInstance(trips, list)
		self.assertEqual(3, len(trips))
		self.assertEqual('324_634_200111', trips[0]['id'])

	## you must start the server in background first
	## and it is recommended to run demo database fill
	## for all the following test
	def test_high_load_sync(self):
		req_start = time.time()
		for i in range(100):
			x = requests.get('http://localhost:8080/vehicles_positions&preventCache=' + str(random()))
			if x.status_code != 200:
				print('req ' + str(i) + ' failed')

		self.assertLess(time.time() - req_start, 1)

	@staticmethod
	async def async_download(urls):
		async with aiohttp.ClientSession() as session:
			for url in urls:
				async with session.get(url) as resp:
					if resp.status != 200:
						print('req ' + url + ' failed')
					if resp.status == 200:
						await resp.read()

	def test_high_load_vehicle_positions(self):
		req_start = time.time()
		asyncio.run(TestServer.async_download(['http://localhost:8080/vehicles_positions&preventCache=' + str(i) for i in range(100)]))

		self.assertLess(time.time() - req_start, 1)

	def test_high_load_trips(self):
		req_start = time.time()
		x = requests.get('http://localhost:8080/vehicles_positions&preventCache=' + str(random()))
		content = json.loads(x.content)
		asyncio.run(TestServer.async_download(['http://localhost:8080/trip.' + trip['properties']['gtfs_trip_id'] + '&preventCache=' + trip['properties']['gtfs_trip_id'] for trip in content['features']]))

		self.assertLess(time.time() - req_start, 1)
		self.assertGreater(len(content['features']), 100)

	def test_high_load_tails(self):
		req_start = time.time()
		x = requests.get('http://localhost:8080/vehicles_positions&preventCache=' + str(random()))
		content = json.loads(x.content)
		asyncio.run(TestServer.async_download(['http://localhost:8080/tail.' + trip['properties']['gtfs_trip_id'] + '&preventCache=' + trip['properties']['gtfs_trip_id'] for trip in content['features']]))

		self.assertLess(time.time() - req_start, 1)
		self.assertGreater(len(content['features']), 100)

	def test_high_load_plot(self):
		times = []
		for i in range(1000):
			req_start = time.time()
			asyncio.run(TestServer.async_download(['http://localhost:8080/vehicles_positions&preventCache=' + str(random()) for _ in range(100)]))
			req_end = time.time()
			# self.assertLess(req_end - req_start, 1)
			times.append(req_end - req_start)
			sleep(0.1)

		mu = np.mean(times)
		sigma = np.std(times)
		count, bins, ignored = plt.hist(times, 30, density=True)
		plt.plot(bins, 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(- (bins - mu) ** 2 / (2 * sigma ** 2)), linewidth=2, color='r')
		# plt.savefig('books_read.pdf')
		plt.show()


	## skipp this test,
	## due to the test database contains old data the server does not find any trip
	## because it finds trips not older 10 minutes
	# def test_get_vehicles_positions(self):
	# 	server = Server('vehicle_positions_test_database')
	#
	# 	all_veh = server.get_vehicles_positions()
	#
	# 	self.assertIsInstance(all_veh, dict)
	# 	self.assertEqual(149, len(all_veh['features']))
	# 	self.assertEqual('Benice', all_veh['features'][0]['properties']['headsign'])

# if __name__ == '__main__':
# 	unittest.main()
