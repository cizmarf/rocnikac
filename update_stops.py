import argparse
import logging
from urllib.request import Request

import mysql.connector

from common_functions import headers
from common_functions import downloadURL
from common_functions import sql_run_transaction
from common_functions import sql_get_result


class Dictlist(dict):
	def __setitem__(self, key, value):
		try:
			self[key]
		except KeyError:
			super(Dictlist, self).__setitem__(key, [])
		self[key].append(value)


def insert(stops, to_insert, id_parent, parent_id):
	mydb = mysql.connector.connect(
			host="localhost",
			database="vehicles_info",
			user="vehicles_access",
			passwd="my_password"
		)
	mycursor = mydb.cursor(prepared=True)

	del stops[parent_id]
	sql_run_transaction(mydb, mycursor, 'INSERT IGNORE INTO stops (stop_id, stop_name, lat, lon, parent_id_stop) VALUES (%s, %s, %s, %s, ' + str(id_parent) + ')', [tuple(t) for t in to_insert])
	for e in to_insert:
		if e[0] in stops:
			insert(stops, stops[e[0]], sql_get_result(mycursor, 'SELECT id_stop FROM stops WHERE stop_id = %s', (e[0], ))[0][0], e[0])


def run_update_stops_script():
	json_stops = downloadURL(Request('https://api.golemio.cz/v1/gtfs/stops', headers=headers))
	stops = Dictlist()

	for jstop in json_stops["features"]:
		stop_id = jstop["properties"]["stop_id"]
		stop_parent_id = jstop["properties"]["parent_station"]
		lon = jstop["geometry"]["coordinates"][0]
		lat = jstop["geometry"]["coordinates"][1]
		stop_name = jstop["properties"]["stop_name"]
		stop = [stop_id, stop_name, lat, lon]
		stops[stop_parent_id] = stop

	insert(stops, stops[""], 'NULL', '')


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--log", default="../stop_update.log", type=str, help="Name of logging file")
	args = parser.parse_args()

	logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=args.log, filemode='w')
	logging.info("Program has started")

	run_update_stops_script()

	logging.info("Program has finished")
