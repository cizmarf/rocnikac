import json
from urllib.request import urlopen, Request

import aiohttp


class Network:
	headers = {
		'Content-Type': 'application/json; charset=utf-8',
		'x-access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNpem1hcmZpbGlwQGdtYWlsLmNvbSIsImlkIjo3NiwibmFtZSI6bnVsbCwic3VybmFtZSI6bnVsbCwiaWF0IjoxNTcwNTQ2MTU2LCJleHAiOjExNTcwNTQ2MTU2LCJpc3MiOiJnb2xlbWlvIiwianRpIjoiMzAxYWNhNDUtNGRlNC00ZDRmLWI4NzAtMzQwMDQ5OTM1MzBhIn0.4rCELzCNY8XOSvjqQA7cKocPGJ8D2ezhXiWUkIRUNjg'
	}

	vehicles_positions = 'https://api.golemio.cz/v1/vehiclepositions'
	# stops = 'https://api.golemio.cz/v1/gtfs/stops'
	trips = 'https://api.golemio.cz/v1/gtfs/trips'

	@staticmethod
	def stops(limit: int = 10000, offset: int = 0) -> str:
		return 'https://api.golemio.cz/v1/gtfs/stops' + \
			   '?limit=' + str(limit) + '&offset=' + str(offset)

	@staticmethod
	def trip_by_id(trip_id: str) -> str:
		return 'https://api.golemio.cz/v1/gtfs/trips/' + \
			   str(trip_id) + '?includeShapes=true&includeStopTimes=true&includeStops=true'

	@staticmethod
	def download_URL(url: str, header: dict = None) -> str:
		try:
			if header is None:
				header = Network.headers
			request = Request(url, headers=header)
			webURL = urlopen(request)
			response_body = webURL.read()
			encoding = webURL.info().get_content_charset('utf-8')
			return response_body.decode(encoding)
		except Exception as e:
			raise IOError(e)


	@staticmethod
	def download_URL_to_json(url: str, header: dict = None) -> dict:
		return json.loads(Network.download_URL(url, header))

	@staticmethod
	async def download_async_URL(url: str, header: dict = None) -> str:
		try:
			if header is None:
				header = Network.headers

			async with aiohttp.ClientSession(headers=header) as s:
				resp = await s.get(url)
				if resp.status != 200:
					raise IOError("Get async url failed.")
				response_body = await resp.text(encoding='utf-8')
				return response_body
		except Exception as e:
			raise IOError(e, url)

	@staticmethod
	async def download_async_URL_to_json(url: str, header: dict = None) -> dict:
		json_text = await Network.download_async_URL(url, header)
		return json.loads(json_text)