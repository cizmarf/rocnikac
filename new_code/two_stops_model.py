from __future__ import annotations

import lzma
import math
import pickle
import warnings
from collections import namedtuple, Set
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

import lib
from file_system import File_system
import numpy as np
import alphashape
from skimage.metrics import mean_squared_error
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

class Norm_data:

	# shape_dist_trav from departure stop,
	# time since departure stop,
	# no of sec since midnight,
	# it trip,
	# timestamp of sample creation
	def __init__(self, shapes, coor_times, day_times, ids_trip, timestamps):
		if not len(shapes) == len(day_times) == len(coor_times) == len(ids_trip) == len(timestamps):
			raise IOError("Norm_data request same length lists")
		self.data = np.array([shapes, coor_times, day_times, ids_trip, timestamps])

	def get_shapes(self):
		return self.data[0]

	def get_coor_times(self):
		return self.data[1]

	def get_day_times(self):
		return self.data[2]

	def get_ids_trip(self):
		return self.data[3]

	def get_timestamps(self):
		return self.data[4]

	def __len__(self):
		return self.data.shape[1]

	def __iter__(self):
		row = namedtuple('normDataRow', 'shape coor_time day_time id_trip timestamp')
		for i in range(self.data.shape[1]):
			yield row(shape=self.get_shapes()[i],
					  coor_time=self.get_coor_times()[i],
					  day_time=self.get_day_times()[i],
					  id_trip=self.get_ids_trip()[i],
					  timestamp=self.get_timestamps()[i])

	def remove_items_by_id_trip(self, trip_id_time: Set, id_to_time_map: dict):
		indices = list(np.where(
			np.isin(self.get_ids_trip(), list(trip_id_time)) == True)[0])
		indices_out = []
		# indices = set(indices)
		two_hours_sec = 60 * 60 * 2

		for idx in indices:
			id_trip = self.get_ids_trip()[idx]
			time_of_sample = self.get_timestamps()[idx].timestamp()

			for error_time in id_to_time_map[id_trip]:
				error_time = error_time.timestamp()
				if error_time - two_hours_sec < time_of_sample < error_time + two_hours_sec:
					indices_out.append(idx)

		self.data = np.delete(self.data, indices_out, 1)


class Super_model:

	model_path = "../../data/models/"

	def __init__(self, distance: int, norm_data: Norm_data = None,
				 dep_stop = None, arr_stop = None, bss_or_hol = None):
		self.model = None
		self.distance = distance
		self.norm_data = norm_data
		self.dep_stop = dep_stop
		self.arr_stop = arr_stop
		self.bss_or_hol = bss_or_hol

	# predicts real delay
	def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
		pass

	# estimates time for given data
	def predict_standard(self, norm_shape_dist_trv, update_time):
		pass

	def get_name(self):
		pass

	def get_model(self) -> Super_model:
		return self.model

	def save_model(self, path = File_system.all_models):
		with lzma.open((
				Path(path) / (str(self.dep_stop) + "_" + str(self.arr_stop) + "_" + self.bss_or_hol)
			).with_suffix(".model"), "wb") as model_file:
			pickle.dump(self, model_file)



# model returns normal delay as a trip at departure stop has no delay

class Two_stops_model:

	TRAVEL_TIME_LIMIT = 7200  # 2 hours
	SECONDS_A_DAY = 24 * 60 * 60
	REMOVE_ALPHA_TIMES = 2
	VEHICLE_ARRIVED_MARGIN = 200  # if vehicle is less then 200 m from arr stop it is considered to be arrived
	REDUCE_VARIANCE_RATE = 40


	class Linear_model(Super_model):

		# distance between the stops, time between the stops
		def __init__(self, distance):
			super().__init__(distance)
			self.distance = distance

		# distance traveled from departure stop, all in seconds
		def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
			if departure_time >= Two_stops_model.SECONDS_A_DAY:
				departure_time -= Two_stops_model.SECONDS_A_DAY

			if arrival_time >= Two_stops_model.SECONDS_A_DAY:
				arrival_time -= Two_stops_model.SECONDS_A_DAY

			if update_time >= Two_stops_model.SECONDS_A_DAY:
				update_time -= Two_stops_model.SECONDS_A_DAY

			time_diff = (arrival_time - departure_time) % Two_stops_model.SECONDS_A_DAY
			norm_update_time = math.fmod(update_time - departure_time, Two_stops_model.SECONDS_A_DAY)

			if norm_update_time < - Two_stops_model.SECONDS_A_DAY / 2:
				norm_update_time += Two_stops_model.SECONDS_A_DAY

			if norm_update_time > Two_stops_model.SECONDS_A_DAY / 2:
				norm_update_time -= Two_stops_model.SECONDS_A_DAY

			ratio = norm_shape_dist_trv / self.distance
			estimated_time_progress = time_diff * ratio
			return norm_update_time - estimated_time_progress  # returns delay -> negative delay means a bus is faster

		def predict_standard(self, norm_shape_dist_trv, update_time):
			print("predict standard linear should not occurs")
			pass

		def get_name(self):
			return "Linear"

		def save_model(self, path = File_system.all_models):
			# save linear model does not make any sense
			pass


	class Polynomial_model(Super_model):

		def __init__(self, distance, norm_data: Norm_data, dep_stop, arr_stop, bss_or_hol):
			super().__init__(distance, norm_data, dep_stop, arr_stop, bss_or_hol)
			self.min_day_time = min(self.norm_data.get_day_times())
			self.max_day_time = max(self.norm_data.get_day_times())
			self._train_model()

		def _train_model(self):
			input_data = np.array([self.norm_data.get_shapes(), self.norm_data.get_day_times()]).transpose()
			input_data = np.pad(input_data, ((0, 0), (0, 1)), constant_values=1)

			output_data = np.array(self.norm_data.get_coor_times())

			X_train, X_test, y_train, y_test = train_test_split(input_data, output_data, test_size=0.33, random_state=42)

			best_degree = 1
			best_error = float('inf')  # maxint

			# TODO delate with
			with warnings.catch_warnings():
				warnings.simplefilter("ignore")

				for degree in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
					model = make_pipeline(PolynomialFeatures(degree), Ridge(), verbose=0)
					model.fit(X_train, y_train)
					pred = model.predict(X_test)
					error = mean_squared_error(y_test, pred)
					if error < best_error:
						best_degree = degree
						best_error = error

				self.model = make_pipeline(PolynomialFeatures(best_degree), Ridge())
				self.model.fit(input_data, output_data)
				pred = self.model.predict(input_data)
				self.rmse = math.sqrt(mean_squared_error(output_data, pred))
				self.degree = best_degree
				print('degree ' + str(best_degree))

				del self.norm_data  # deletes norm data structure because it is no more needed

		def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
			if departure_time >= Two_stops_model.SECONDS_A_DAY:
				departure_time -= Two_stops_model.SECONDS_A_DAY

			if arrival_time >= Two_stops_model.SECONDS_A_DAY:
				arrival_time -= Two_stops_model.SECONDS_A_DAY

			if update_time >= Two_stops_model.SECONDS_A_DAY:
				update_time -= Two_stops_model.SECONDS_A_DAY

			if self.max_day_time < update_time:  # if in estimator area
				departure_time -= update_time - self.max_day_time
				arrival_time -= update_time - self.max_day_time
				update_time = self.max_day_time

			if self.min_day_time > update_time:
				departure_time += self.min_day_time - update_time
				arrival_time += self.min_day_time - update_time
				update_time = self.min_day_time

			time_diff = (arrival_time - departure_time) % Two_stops_model.SECONDS_A_DAY
			norm_update_time = math.fmod(update_time - departure_time, Two_stops_model.SECONDS_A_DAY)

			if norm_update_time < - Two_stops_model.SECONDS_A_DAY / 2:
				norm_update_time += Two_stops_model.SECONDS_A_DAY

			if norm_update_time > Two_stops_model.SECONDS_A_DAY / 2:
				norm_update_time -= Two_stops_model.SECONDS_A_DAY

			input_data = np.array([norm_shape_dist_trv, update_time, 1]).reshape(1,-1)
			prediction = self.model.predict(input_data)  # estimation of coor time
			arrival_data = np.array([self.distance, arrival_time, 1]).reshape(1,-1)
			model_delay = self.model.predict(arrival_data) - time_diff  # no of seconds difference between scheduled arrival and model estimation
			return model_delay[0] + norm_update_time - prediction[0]

		def predict_standard(self, norm_shape_dist_trv, update_time):
			input_data = np.pad(np.array(
				[norm_shape_dist_trv, update_time]).T, ((0, 0), (0, 1)), constant_values=1)
			return self.model.predict(input_data)

		def get_rmse(self):
			return self.rmse

		def get_name(self):
			return "Poly"

	# norm_data is dict of shapes, coor_times ands day_times, ids_trip
	def __init__(self, dep_id_stop: int, arr_id_stop: int, distance: int, bss_or_hol: str):
		self.dep_id_stop = dep_id_stop
		self.arr_id_stop = arr_id_stop
		self.distance = distance
		self.max_travel_time = 0
		self.shapes = []
		self.coor_times = []
		self.day_times = []
		self.timestamps: List[datetime] = []
		self.ids_trip = []
		self.bss_or_hol = bss_or_hol

	def add_row(self, shape: int, dep_time: int, day_time: datetime, id_trip: int, arr_time: int, last_stop_delay: int):

		# ignores data if a bus is much more longer time on its way than usual
		# if day_time - dep_time < Two_stops_model.TRAVEL_TIME_LIMIT:
		self.shapes.append(shape)
		self.day_times.append(lib.time_to_sec(day_time))
		self.timestamps.append(day_time)
		self.ids_trip.append(id_trip)

		self.coor_times.append(Two_stops_model._get_coor_time(lib.time_to_sec(day_time), dep_time, last_stop_delay))

		if arr_time - dep_time > self.max_travel_time and arr_time > dep_time:
			self.max_travel_time = arr_time - dep_time

		# vehicle passes midnight
		if arr_time - dep_time + Two_stops_model.SECONDS_A_DAY> self.max_travel_time and arr_time <= dep_time:
			self.max_travel_time = arr_time - dep_time + Two_stops_model.SECONDS_A_DAY


	def create_model(self):
		self.norm_data = Norm_data(self.shapes, self.coor_times, self.day_times, self.ids_trip, self.timestamps)

		if len(self.norm_data) == 0:
			self.model = Two_stops_model.Linear_model(self.distance)
			return

		self._reduce_errors()

		print('Samples reduced to ' + str(len(self.norm_data)))

		# more than 10 x 4 data samples per km needed, distance between stops is already filtered by sql query
		if len(self.norm_data) < self.distance * 0.001 * 10 * 4:
			print(str(len(self.norm_data)) + ' is not enough')
			self.model = Two_stops_model.Linear_model(self.distance)
			return

		poly_model = Two_stops_model.Polynomial_model(self.distance, self.norm_data, self.dep_id_stop, self.arr_id_stop, self.bss_or_hol)
		print('Poly model generated with rmse ' + str(poly_model.rmse))

		if poly_model.degree == 1:
			self.model = Two_stops_model.Linear_model(self.distance)
			return

		self.model = poly_model
		return

	def __len__(self):
		assert len(self.shapes) == len(self.day_times) == len(self.coor_times) == len(self.ids_trip)
		return len(self.shapes)

	def _reduce_errors(self):
		# removes trips delayed more then alpha times
		trips_to_remove = set()
		trip_times_to_remove = dict()
		coor_times = self.norm_data.get_coor_times()
		norm_shapes = np.divide(self.norm_data.get_shapes(), 100)

		# coordinates times and distance are semi linear dependent

		rate = np.divide(coor_times, norm_shapes, where=norm_shapes!=0,) #!= np.array(None)
		for i in range(len(rate)):
			if rate[i] == np.inf:
				rate[i] = 0.0
			if rate[i] is None:
				rate[i] = 0.0
			# low shape distance travelled and a little higher coor time
			# may cause false indicating the samples as high variance
			# if norm_shapes[i] < 2:
			# 	rate[i] = rate[i] / 2.0

		if max(norm_shapes) > 1:
			tmp = []
			for i in range(len(rate)):
				tmp.append(rate[i] * (1 - ((max(norm_shapes) - norm_shapes[i]) / max(norm_shapes))))

			rate = np.array(tmp)
		# print("mena:", abs(rate - rate.mean()))
		# print("std:", rate.std())

		# print('median ' + str(np.median(np.array(coor_times))))
		# gets indices of high variance
		high_variance = np.where((
				abs(rate - np.median(np.array(rate))) > rate.std() * 4 + (np.median(np.array(rate))) # / Two_stops_model.REDUCE_VARIANCE_RATE)
			).astype(int) == 1)[0]

		# for all indicated indices gets trips ids
		# and creates dictionary of day times of all corrupted samples
		for hv in high_variance:
			trip_id = self.norm_data.get_ids_trip()[hv]
			trips_to_remove.add(trip_id)

			if trip_id in trip_times_to_remove:
				trip_times_to_remove[trip_id].append(self.norm_data.get_timestamps()[hv])

			else:
				trip_times_to_remove[trip_id] = [self.norm_data.get_timestamps()[hv]]

		self.norm_data.remove_items_by_id_trip(trips_to_remove, trip_times_to_remove)

	@staticmethod
	def _get_coor_time(day_time, dep_time, last_stop_delay):
		if day_time - dep_time - last_stop_delay < - Two_stops_model.SECONDS_A_DAY / 2:
			return (day_time - dep_time - last_stop_delay + Two_stops_model.SECONDS_A_DAY)
		else:
			return (day_time - dep_time - last_stop_delay)
