import asyncio
import time
from typing import Any, Iterable, List, Tuple, Callable
import os
import aiohttp
import requests

headers = {
		'Content-Type': 'application/json; charset=utf-8',
		'x-access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNpem1hcmZpbGlwQGdtYWlsLmNvbSIsImlkIjo3NiwibmFtZSI6bnVsbCwic3VybmFtZSI6bnVsbCwiaWF0IjoxNTcwNTQ2MTU2LCJleHAiOjExNTcwNTQ2MTU2LCJpc3MiOiJnb2xlbWlvIiwianRpIjoiMzAxYWNhNDUtNGRlNC00ZDRmLWI4NzAtMzQwMDQ5OTM1MzBhIn0.4rCELzCNY8XOSvjqQA7cKocPGJ8D2ezhXiWUkIRUNjg'
	}

def image_name_from_url(url: str) -> str:
	return url.split("/")[-1]

def just_sleep():
	print("sleep starts")
	time.sleep(2)
	print("sleep ends")

async def donwload_aio(urls: Iterable[str]) -> List[Tuple[str, bytes]]:
	async def download(url: str) -> Tuple[str, bytes]:
		print(f"Start downloading {url}")
		async with aiohttp.ClientSession(headers=headers) as s:
			resp = await s.get(url)
			out = image_name_from_url(url), await resp.read()
		print(f"Done downloading {url}")
		return out

	# just_sleep()
	return await asyncio.gather(*[download(url) for url in urls])


def download_all(urls: Iterable[str]) -> List[Tuple[str, bytes]]:
	def download(url: str) -> Tuple[str, bytes]:
		print(f"Start downloading {url}")
		with requests.Session(headers=headers) as s:
			resp = s.get(url)
			out= image_name_from_url(url), resp.content
		print(f"Done downloading {url}")
		return out
	return [download(url) for url in urls]

if __name__ == "__main__":
	# Get list of images from dogs API
	URL = "https://dog.ceo/api/breed/hound/images"
	images = requests.get(URL).json()["message"]
# Take only 200 images to not run into issues with gather	 
	reduced = ['https://api.golemio.cz/v1/gtfs/trips/317_166_200316?includeShapes=true&includeStopTimes=true&includeStops=true',
			   'https://api.golemio.cz/v1/gtfs/trips/303_1100_200701?includeShapes=true&includeStopTimes=true&includeStops=true',
			   'https://api.golemio.cz/v1/gtfs/trips/317_38_200601?includeShapes=true&includeStopTimes=true&includeStops=true']
	# st = time.time()
	# images_s = download_all(reduced)
	# print(f"Synchronous exec took {time.time() - st} seconds")
	st = time.time()
	images_a = asyncio.run(donwload_aio(reduced))
	print(f"Asynchronous exec took {time.time() - st} seconds")

# async def main():
#	 print('Hello ...')
#	 await asyncio.sleep(1)
#	 print('... World!')
# 
# # Python 3.7+
# asyncio.run(main())
# asyncio.run(main())