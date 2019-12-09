
import json
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen, Request
from jsonschema import validate

from common_functions import headers
from common_functions import downloadURL
from common_functions import GI


class Schemata:
	vehicle_positions_schema = {
		GI.features : [{
			GI.properties : {
				GI.trip : {
					GI.gtfs_trip_id : {"type" : "str"},
					GI.gtfs_route_short_name : {"type" : "str"}
				},
				"last_position" : {
					"origin_time" : {"type" : "time"},
					"origin_timestamp" : {"type" : "datetime"},
					"gtfs_shape_dist_traveled" : {"type" : "float"},
					"delay" : {"type" : "int"}
				}
			},
			GI.geometry : {
				GI.coordinates : [
					{"type" : "float"},
					{"type" : "float"}
				]
			}
		}]
	}

	trip_schema = {
		"trip_headsign" : {"type" : "str"},
		"stop_times" : [{
			"arrival_time" : {"type" : "time"},
			"departure_time" : {"type" : "time"},
			"shape_dist_traveled" : {"type" : "float"},
			"stop_id" : {"type" : "str"},
			"stop" : {
				"properties" : {
					"stop_lon" : {"type" : "float"},
					"stop_lat" : {"type" : "float"},
					"stop_name" : {"type" : "str"}
				}
			}
		}],
		"shapes" : [{
			"properties": {
				GI.shape_dist_traveled : {"type" : "float"}
			},
			"geometry" : {
				GI.coordinates : [
					{"type" : "float"},
					{"type" : "float"}
				]
			}
		}]
	}

	stops_schema = {
		"features" : [{
			GI.properties : {
				"stop_id" : {"type" : "str"},
				"parent_station" : {"type" : "str"},
				"stop_name" : {"type" : "str"}
			},
			"geometry" : {
				GI.coordinates : [
					{"type" : "float"},
					{"type" : "float"}
				]
			}
		}]
	}


def check_url_schema(name: str, url: str, schema: dict, ret: tuple = False):

	def check_json(json: dict, schema: dict) -> list:
		list_of_errors = []

		def is_type(e: dict) -> bool:
			if len(e) == 1 and "type" in e:
				return True
			else:
				return False

		def check_type(j, e) -> bool:
			try:
				if e["type"] == "time":
					time.strptime(j, '%H:%M:%S')
					return True

				if e["type"] == "datetime":
					time.strptime(j, '%Y-%m-%dT%H:%M:%S.%fZ')
					return True

				import builtins
				getattr(builtins, e["type"])(j)
				return True

			except ValueError:
				return False

		def recursive(json: dict, schema: dict, keys: list) -> list:
			if type(schema) is list and len(schema) == 1:
				if len(json) == 0:
					list_of_errors.append(keys + ["Nothing to check"])
				else:
					recursive(json[0], schema[0], keys)

			elif type(schema) is list and len(schema) > 1:
				for j, e in zip(json, schema):
					if is_type(e):
						if not check_type(j, e):
							list_of_errors.append(keys + [(schema["type"], json)])

			elif is_type(schema):
				if not check_type(json, schema):
					list_of_errors.append(keys + [(schema["type"], json)])

			else:
				for key in schema:
					if key not in json:
						list_of_errors.append(keys + [key])
					else:
						recursive(json[key], schema[key], keys + [key])

		recursive(json, schema, [])
		return list_of_errors

	print("Checking", name , "json schema:")
	json = downloadURL(Request(url, headers=headers))
	out = check_json(json, schema)
	print("Checking", name, "json schema has finished.")

	if len(out) > 0:
		print("Some errors has found:", flush=True)

		for e in out:
			if type(e[-1]) is tuple:
				print("Value error: '", e[-1][0], "' expected but '", e[-1][1], "' given. At ", sep='', end='', file=sys.stderr)

			elif e[-1] == "Nothing to check":
				print("Nothing to check. At ", end='', file=sys.stderr)

			else:
				print("Index '", e[-1], "' has not found. At ", sep='', end='', file=sys.stderr)

			for k in e[:-1]:
				print('[', k, ']', sep='', end='', file=sys.stderr)

			print('.', file=sys.stderr, flush=True)

		if ret:
			print("Return has failed.", file=sys.stderr, flush=True)

		print()

	else:
		print(name, "json matches the schema.")
		print()

		if ret:
			cur_json = json

			for k in ret:
				if k in cur_json or type(cur_json) is list:
					cur_json = cur_json[k]

				else:
					return False

			return cur_json
		return False


if __name__ == "__main__":
	try:
		trip_id = check_url_schema("Vehicle Positions", 'https://api.golemio.cz/v1/vehiclepositions?limit=20', Schemata.vehicle_positions_schema, ret=(GI.features, 0, GI.properties, GI.trip, GI.gtfs_trip_id))
		if trip_id:
			check_url_schema("Trip", 'https://api.golemio.cz/v1/gtfs/trips/' + trip_id + '?includeShapes=true&includeStopTimes=true', Schemata.trip_schema)
		check_url_schema("Stops", 'https://api.golemio.cz/v1/gtfs/stops', Schemata.stops_schema)

	except URLError as e:
		print(e)

