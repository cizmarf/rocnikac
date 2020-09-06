import unittest
from network import Network

class TestNetwork(unittest.TestCase):
	def test_stops(self):
		self.assertEqual(Network.stops(100, 2), "https://api.golemio.cz/v1/gtfs/stops?limit=100&offset=2")

	def test_trip_by_id(self):
		self.assertEqual(Network.trip_by_id(1), "https://api.golemio.cz/v1/gtfs/trips/1?includeShapes=true&includeStopTimes=true&includeStops=true")

	def test_download_URL_download_URL_to_json(self):
		file_json = Network.download_URL_to_json(Network.trips)

		assert isinstance(file_json, list)

	def test_download_async_URL_download_async_URL_to_json(self):
		import asyncio
		import time

		async def download(url):
			return await Network.download_async_URL_to_json(url)

		async def make_download_ready():
			gather = []
			offset = 0
			for i in range(10):
				gather.append(download(Network.stops(10, offset)))
				offset += 10

			return await asyncio.gather(*gather)

		start = time.time()

		result = asyncio.run(make_download_ready())

		end = time.time()
		async_time = end - start

		self.assertEqual(len(result), 10)
		assert isinstance(result[0], dict)

		start = time.time()

		offset = 0
		for i in range(10):
			Network.download_URL_to_json(Network.stops(10, offset))
			offset += 10

		end = time.time()
		serial_time = end - start

		# This assert success depends on internet
		# in case of slow internet connection or any different problem this test may fail
		# please disable  this assert manually
		self.assertGreater(serial_time, async_time)


if __name__ == '__main__':
	unittest.main()
