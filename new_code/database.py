import mysql.connector


class Database:

	def __init__(self):
		self.connection = mysql.connector.connect(
			host="localhost",
			database="vehicle_positions_database",
			user="vehicles_access",
			passwd="my_password",
			autocommit=True
		)
		self.cursor_prepared = self.connection.cursor(prepared=True)
		self.cursor = self.connection.cursor(buffered=True)

	def execute_transaction_commit_rollback(self, sql_query, params=()):
		try:
			self.execute('START TRANSACTION;')
			ret = self.execute(sql_query, params)
			self.execute('COMMIT;')
			return ret
		except Exception as e:
			self.execute('ROLLBACK;')
			print("rollback")
			raise IOError(e)

	def execute_fetchall(self, sql_query, params=()):
		self.cursor.execute(sql_query, params)
		return self.cursor.fetchall()

	def execute(self, sql_query, params=()):
		self.cursor.execute(sql_query, params)

	def execute_many(self, sql_query, params=()):
		# try:
		self.cursor.executemany(sql_query, params)
		# connection.commit()
		# except mysql.connector.errors.IntegrityError as e:
		# 	print(e)
		# 	print("Query failed", sql_query, "params:", params)
		# except Exception as e:
		# 	print(e)
		# 	print("Query failed", sql_query, "params:", params)

	def commit(self):
		self.connection.commit()

	def rollback(self):
		self.connection.rollback()
