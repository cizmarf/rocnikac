import argparse
import unittest
from pathlib import Path

from database import Database
from download_and_process import main
from file_system import File_system


class FillDatabase(unittest.TestCase):
	# def test_something(self):
	# 	self.assertEqual(True, False)

	database_connection = Database("vehicle_positions_test_database")

	parser = argparse.ArgumentParser()
	parser.add_argument("--static_data", default=True, type=bool, help="Fill with static data or dynamic real-time data.")
	parser.add_argument("--static_demo", default=False, type=bool,
						help="Use only if static data in use, time of insert sets now and wait 20 s for next file.")
	parser.add_argument("--update_time", default=20, type=int, help="Time to next request")
	parser.add_argument("--update_error", default=20, type=int, help="Update time if network error occurred")
	parser.add_argument("--clean_old", default=-1, type=int, help="Deletes all trips inactive for more than set minutes")
	args = parser.parse_args([] if "__file__" not in globals() else None)

	# def testTest(self):
	# 	self.assertEqual(1,2)

	def testInsertData(self):
		File_system.static_vehicle_positions = Path("/Users/filipcizmar/Documents/rocnikac/raw_data_unittest/")

		main(FillDatabase.database_connection, FillDatabase.args)

		trips = FillDatabase.database_connection.execute_fetchall('SELECT * FROM trips')
		print(trips)
		print(len(trips))
		self.assertGreater(len(trips), 1)


if __name__ == '__main__':
	unittest.main()
