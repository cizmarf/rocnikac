#!/usr/bin/env python3
import time

from database import Database

from two_stops_model import Two_stops_model

import lib


class Build_models:
	## Builds models of rides between all pairs of stops

	def __init__(self):
		self.database_connection = Database('vehicle_positions_statistic_database')

		# demo app needs aprox 30 secs to fetch
		# in production it may takes longer time to fetch all data
		self.database_connection.execute('SET GLOBAL connect_timeout=600')
		self.database_connection.execute('SET GLOBAL wait_timeout=600')
		self.database_connection.execute('SET GLOBAL interactive_timeout=600')

		self.stop_to_stop_data = []

	def add_row(self, sts_row):
		if lib.is_business_day(sts_row[6]):
			self.business_day_model.add_row(
				sts_row[7],  # shape distance traveled from dep stop
				sts_row[3].seconds,  # departure time
				sts_row[6],  # day time
				sts_row[0],  # id trip
				sts_row[4].seconds,  # arr time
				sts_row[8])  # last_stop_delay
		else:
			self.nonbusiness_day_model.add_row(
				sts_row[7],
				sts_row[3].seconds,
				sts_row[6],
				sts_row[0],
				sts_row[4].seconds,
				sts_row[8])

	def get_data(self):
		# offset, limit set to 0, in production set appropriate values
		# and change function behavior
		self.stop_to_stop_data = self.database_connection.execute_procedure_fetchall(
			'get_all_pairs_of_stops', (0, 0, 1500))

	## This query selects all pairs of stops, the second leads the first,
	# by schedule and joins trip coordinates.
	# It order the result by id_stop and id_leading_stop

	def main(self):

		# no data fetched
		if len(self.stop_to_stop_data) == 0:
			print("no data fetched")
			return
		else:
			req_start = time.time()
			# For all stops pairs two models are created (business days and nonbusiness days)
			# dep stop id, arr stop id, distance between stops
			self.business_day_model = Two_stops_model(
				self.stop_to_stop_data[0][1],
				self.stop_to_stop_data[0][2],
				self.stop_to_stop_data[0][5],
				"bss")
			self.nonbusiness_day_model = Two_stops_model(
				self.stop_to_stop_data[0][1],
				self.stop_to_stop_data[0][2],
				self.stop_to_stop_data[0][5],
				"hol")

			for sts_row in self.stop_to_stop_data:

				# Because of ordered result all stop pairs coordinates are sorted in row by stops,
				# if new stop pair found a new model pair is created from current data
				# could be nonbusiness model use as well
				if self.business_day_model.dep_id_stop != sts_row[1] or \
						self.business_day_model.arr_id_stop != sts_row[2]:

					print('Building models between ' + str(self.business_day_model.dep_id_stop) + ' and ' + str(self.business_day_model.arr_id_stop))
					print('bss: ' + str(len(self.business_day_model.shapes)) + ', hol: ' + str(len(self.nonbusiness_day_model.shapes)))

					if len(self.business_day_model) > 0:
						self.business_day_model.create_model()
						self.business_day_model.model.save_model()

					if len(self.nonbusiness_day_model) > 0:
						self.nonbusiness_day_model.create_model()
						self.nonbusiness_day_model.model.save_model()

					print((self.business_day_model.model.get_name() if len(self.business_day_model) > 0 else '_') + ' ' + (self.nonbusiness_day_model.model.get_name() if len(self.nonbusiness_day_model) > 0 else '_') + ' models created in ' + str(time.time() - req_start) + ' seconds')
					req_start = time.time()

					self.business_day_model = Two_stops_model(
						sts_row[1],  # dep stop id
						sts_row[2],  # arr stop id
						sts_row[5],  # distance between stops
						"bss"
					)
					self.nonbusiness_day_model = Two_stops_model(
						sts_row[1],
						sts_row[2],
						sts_row[5],
						"hol"
					)


				self.add_row(sts_row)

			print('Building models between ' + str(self.business_day_model.dep_id_stop) + ' and ' + str(self.business_day_model.arr_id_stop))
			print('bss: ' + str(len(self.business_day_model.shapes)) + ', hol: ' + str(len(self.nonbusiness_day_model.shapes)))

			if len(self.business_day_model) > 0:
				self.business_day_model.create_model()
				self.business_day_model.model.save_model()
			if len(self.nonbusiness_day_model) > 0:
				self.nonbusiness_day_model.create_model()
				self.nonbusiness_day_model.model.save_model()

			print((self.business_day_model.model.get_name() if len(self.business_day_model) > 0 else '_') + ' ' + (self.nonbusiness_day_model.model.get_name() if len(self.nonbusiness_day_model) > 0 else '_') + ' models created in ' + str(time.time() - req_start) + ' seconds')


if __name__ == '__main__':
	bm = Build_models()
	bm.get_data()
	bm.main()
