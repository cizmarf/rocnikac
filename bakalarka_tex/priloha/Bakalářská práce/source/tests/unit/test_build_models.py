import unittest
from datetime import datetime, timedelta

import lib
from build_models import Build_models
from file_system import File_system
from two_stops_model import Two_stops_model


class TestBuil_models(unittest.TestCase):
	def save_specify_model(self, dep = 2, arr = 2374):
		## this function is designed for easy save a model specify by stops ids
		bm = Build_models()
		bm.get_data()

		rows_to_save_bss = []
		rows_to_save_hol = []
		first = True

		for sts_row in bm.stop_to_stop_data:

			if sts_row[1] == dep and sts_row[2] == arr:
				if first:
					bm.business_day_model = Two_stops_model(sts_row[1], sts_row[2], sts_row[5], "bss")
					bm.nonbusiness_day_model = Two_stops_model(sts_row[1], sts_row[2], sts_row[5], "hol")
					first = False

				bm.add_row(sts_row)

				if lib.is_business_day(sts_row[6]):
					rows_to_save_bss.append(sts_row)
				else:
					rows_to_save_hol.append(sts_row)
			else:
				print(len(rows_to_save_bss), len(rows_to_save_hol), str(dep), str(arr))
				if 5649 == len(rows_to_save_bss) and 4222 == len(rows_to_save_hol):
					print('stops:', str(dep), str(arr))
				dep = sts_row[1]
				arr = sts_row[2]
				rows_to_save_bss = []
				rows_to_save_hol = []
				if lib.is_business_day(sts_row[6]):
					rows_to_save_bss.append(sts_row)
				else:
					rows_to_save_hol.append(sts_row)
				bm.business_day_model = Two_stops_model(sts_row[1], sts_row[2], sts_row[5], "bss")
				bm.nonbusiness_day_model = Two_stops_model(sts_row[1], sts_row[2], sts_row[5], "hol")

		if len(bm.business_day_model) > 0:
			bm.business_day_model.create_model()
			# print(bm.business_day_model.model.model.get_params())

			bm.business_day_model.model.save_model('../input_data/')
			File_system.pickle_object(rows_to_save_hol, '../input_data/' + str(dep) + '_' + str(arr) + '_bss.data')
		if len(bm.nonbusiness_day_model) > 0:
			bm.nonbusiness_day_model.create_model()
			# print(bm.nonbusiness_day_model.model.model.get_params())

			bm.nonbusiness_day_model.model.save_model('../input_data/')
			File_system.pickle_object(rows_to_save_hol, '../input_data/' + str(dep) + '_' + str(arr) + '_hol.data')

		# for default parameters
		self.assertEqual(5649, len(rows_to_save_bss))
		self.assertEqual(4222, len(rows_to_save_hol))

	def test_main(self):
		bm = Build_models()
		bm.stop_to_stop_data = [
			(126, 52, 53, timedelta(hours=21, minutes=55, seconds=00), timedelta(hours=21, minutes=58, seconds=00), 3512, datetime(2020, 2, 23, 21, 55, 42), 411, -10),
			(126, 52, 53, timedelta(hours=21, minutes=55, seconds=00), timedelta(hours=21, minutes=58, seconds=00), 3512, datetime(2020, 2, 23, 21, 56, 23), 1011, -10),
			(104, 68, 69, timedelta(hours=21, minutes=37, seconds=00), timedelta(hours=22, minutes=2, seconds=00), 34501, datetime(2020, 2, 23, 21, 37, 17), 24, 17),
			(104, 68, 69, timedelta(hours=21, minutes=37, seconds=00), timedelta(hours=22, minutes=2, seconds=00), 34501, datetime(2020, 2, 23, 21, 37, 59), 124, 52)
		]

		models_generated = 0

		bm.business_day_model = Two_stops_model(bm.stop_to_stop_data[0][1], bm.stop_to_stop_data[0][2], bm.stop_to_stop_data[0][5], "bss")
		bm.nonbusiness_day_model = Two_stops_model(bm.stop_to_stop_data[0][1], bm.stop_to_stop_data[0][2], bm.stop_to_stop_data[0][5], "hol")

		for sts_row in bm.stop_to_stop_data:

			# Because of ordered result all stop pairs coordinates are sorted in row by stops,
			# if new stop pair found a new model pair is created from current data
			# could be nonbusiness model use as well
			if bm.business_day_model.dep_id_stop != sts_row[1] or \
					bm.business_day_model.arr_id_stop != sts_row[2]:

				if len(bm.business_day_model) > 0:
					self.assertEqual(2, len(bm.business_day_model))
					models_generated += 1
				bm.business_day_model = Two_stops_model(
					sts_row[1],  # dep stop id
					sts_row[2],  # arr stop id
					sts_row[5],  # distance between stops
					"bss"
				)
				if len(bm.nonbusiness_day_model) > 0:
					self.assertEqual(2, len(bm.nonbusiness_day_model))
					models_generated += 1
				bm.nonbusiness_day_model = Two_stops_model(
					sts_row[1],
					sts_row[2],
					sts_row[5],
					"hol"
				)

			bm.add_row(sts_row)

		if len(bm.business_day_model) > 0:
			self.assertEqual(2, len(bm.business_day_model))
			models_generated += 1
		if len(bm.nonbusiness_day_model) > 0:
			self.assertEqual(2, len(bm.nonbusiness_day_model))
			models_generated += 1

		self.assertEqual(2, models_generated)

if __name__ == '__main__':
	unittest.main()
