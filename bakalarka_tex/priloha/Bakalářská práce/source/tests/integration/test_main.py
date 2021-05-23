import time
import unittest
from pathlib import Path

from database import Database
from file_system import File_system
from tests import lib_tests
from download_and_process import main


# start simulation of vehicles flow
# uses data captured in half of hour
# between 2020-02-23 20.30.14 and 2020-02-23 20.59.52
# however to the database it saves last update attribute now
class TestMainDemo(unittest.TestCase):
	def test_demo(self):
		lib_tests.drop_all_tables()

		database_connection = Database("vehicle_positions_test_database")
		old_path = File_system.static_vehicle_positions
		File_system.static_vehicle_positions = File_system.cwd / Path("tests/input_data/raw_vehicle_positions_simple/")

		args = lib_tests.get_args_demo()

		req_start = time.time()
		main(database_connection, args)
		req_end = time.time()
		print('seconds ' + str(req_end - req_start))

		File_system.static_vehicle_positions = old_path

	def test_live_demo(self):
		lib_tests.drop_all_tables()

		database_connection = Database("vehicle_positions_test_database")
		# old_path = File_system.static_vehicle_positions
		# File_system.static_vehicle_positions = File_system.cwd / Path("tests/input_data/raw_vehicle_positions_simple/")

		args = lib_tests.get_args_live_demo()

		req_start = time.time()
		main(database_connection, args)
		req_end = time.time()
		print('seconds ' + str(req_end - req_start))

		# File_system.static_vehicle_positions = old_path

if __name__ == '__main__':
	unittest.main()
