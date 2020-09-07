# Code library for tests
import argparse

from database import Database

def drop_all_tables():
	database_connection = Database("vehicle_positions_test_database")

	database_connection.cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

	database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.rides;")
	database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.stops;")
	database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.trip_coordinates;")
	database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.trips;")
	database_connection.cursor.execute("TRUNCATE TABLE vehicle_positions_test_database.headsigns;")
	database_connection.connection.commit()

	database_connection.cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

	database_connection.close()

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("--static_data", default=True, type=bool, help="Fill with static data or dynamic real-time data.")
	parser.add_argument("--static_demo", default=False, type=bool,
						help="Use only if static data in use, time of insert sets now and wait 20 s for next file.")
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--clean_old", default=-1, type=int, help="Deletes all trips inactive for more than set minutes")
	args = parser.parse_args([] if "__file__" not in globals() else None)

	return args
