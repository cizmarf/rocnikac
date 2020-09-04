import mysql.connector


class Database:
	## Sets connection to the database and keeps it during the whole execution
	def __init__(self, database="vehicle_positions_database"):
		self.connection = mysql.connector.connect(
			host="localhost",
			database=database,
			user="vehicles_access",
			passwd="my_password_1234",
			autocommit=True
		)
		self.cursor_prepared = self.connection.cursor(prepared=True)
		self.cursor = self.connection.cursor(buffered=True)

		self.execute(
			'SET @@session.time_zone = "+00:00"'
		)

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

	def execute_procedure_fetchall(self, query, params=()):
		self.cursor.callproc(query, params)
		return_list = []
		for result in self.cursor.stored_results():
			return_list.append(result.fetchall())
		# return self.cursor.stored_results()[0].fetchall()

		# i dont got meaning of the for loop but it is not working otherwise
		if return_list[0] == [] and len(return_list) == 1:
			return_list = []

		if len(return_list) == 1:
			return_list = return_list[0]

		return return_list

	def commit(self):
		self.connection.commit()

	def rollback(self):
		self.connection.rollback()
