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


def insert(to_insert, id_parent, parent_id):
	if id_parent == 'NULL':
		del stops['']
		sql_run_transaction(mydb, mycursor, 'INSERT IGNORE INTO stops (stop_id, stop_name, lon, lat, parent_id_stop) VALUES (%s, %s, %s, %s, NULL)', [tuple(t) for t in to_insert])
	else:
		del stops[parent_id]
		array_of_records = []
		for e in to_insert:
			e.append(id_parent)
			array_of_records.append(tuple(e))
		sql_run_transaction(mydb, mycursor, 'INSERT IGNORE INTO stops (stop_id, stop_name, lat, lon, parent_id_stop) VALUES (%s, %s, %s, %s, %s)', array_of_records)
	for e in to_insert:
		if e[0] in stops:
			insert(stops[e[0]], sql_get_result(mycursor, 'SELECT id_stop FROM stops WHERE stop_id = %s', (e[0], ))[0][0], e[0])



mydb = mysql.connector.connect(
		host="localhost",
		database="vehicles_info",
		user="vehicles_access",
		passwd="my_password"
	)
mycursor = mydb.cursor(prepared=True)

json_stops = downloadURL(Request('https://api.golemio.cz/v1/gtfs/stops', headers=headers))
stops = Dictlist()
for jstop in json_stops["features"]:
	stop_id = jstop["properties"]["stop_id"]
	stop_parent_id = jstop["properties"]["parent_station"]
	lon = jstop["geometry"]["coordinates"][0]
	lat = jstop["geometry"]["coordinates"][1]
	stop_name = jstop["properties"]["stop_name"]
	stop = [stop_id, stop_name, lon, lat]
	stops[stop_parent_id] = stop

	#TODO insertuj rekurzivne podle vlozeneho rodice

insert(stops[""], 'NULL', 'NULL')

	# result = sql_get_result(mycursor, 'SELECT id_stop FROM stops WHERE stop_id = %s', stop_parent_id)[0][0]
	# sql_run_transaction('INSERT IGNORE INTO stops ()')