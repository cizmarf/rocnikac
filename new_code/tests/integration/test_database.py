import unittest

from file_system import File_system


class MyTestCase(unittest.TestCase):

	def testInsertData(self):
		File_system.static_vehicle_positions = Path("/Users/filipcizmar/Documents/rocnikac/raw_data_unittest/")

		main(FillDatabase.database_connection, FillDatabase.args)

		trips = self.database_connection.execute_fetchall('SELECT * FROM trips')
		print(trips)
		print(len(trips))
		self.assertGreater(len(trips), 1)

if __name__ == '__main__':
	unittest.main()
