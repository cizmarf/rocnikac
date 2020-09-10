import unittest


class MyTestCase(unittest.TestCase):
	def test_something(self):
		self.database_connection = Database('vehicle_positions_database')

		# demo app needs aprox 30 secs to fetch
		# in production it may takes longer time to fetch all data
		self.database_connection.execute('SET GLOBAL connect_timeout=600')
		self.database_connection.execute('SET GLOBAL wait_timeout=600')
		self.database_connection.execute('SET GLOBAL interactive_timeout=600')


if __name__ == '__main__':
	unittest.main()
