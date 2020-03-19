from collections import namedtuple, Set

import numpy as np
from skimage.metrics import mean_squared_error
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

class Norm_data:

	def __init__(self, shapes, coor_times, day_times, ids_trip):
		assert len(shapes) == len(day_times) == len(coor_times) == len(ids_trip)
		self.data = np.array([shapes, coor_times, day_times, ids_trip])

	def get_shapes(self):
		return self.data[0]

	def get_coor_times(self):
		return self.data[1]

	def get_day_times(self):
		return self.data[2]

	def get_ids_trip(self):
		return self.data[3]

	def __len__(self):
		return self.data.shape[1]

	def __iter__(self):
		row = namedtuple('Row', 'shape coor_times day_times ids_trip')
		for i in range(len(self.data)):
			yield row(shape=self.get_shapes()[i],
					  coor_times=self.get_coor_times()[i],
					  day_times=self.get_day_times()[i],
					  ids_trip=self.get_ids_trip()[i])

	def remove_items_by_id_trip(self, ids_trip: Set):
		indecies = []
		for i in range(len(self.data)):
			if self.get_ids_trip()[i] in ids_trip:
				indecies.append(i)

		transp = self.data.transpose()
		np.delete(transp, indecies)
		self.data = transp.transpose()
		assert len(self.data) == 4






class Super_model:
	def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
		pass

	def predict_standard(self, norm_shape_dist_trv, update_time):
		pass

	def get_name(self):
		pass


# model returns normal delay as a trip at departure stop has no delay

class Two_stops_model:

	class Linear_model(Super_model):

		# distance between the stops, time between the stops
		def __init__(self, distance):
			self.distance = distance

		# distance traveled from departure stop, all in seconds
		def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
			time_diff = arrival_time - departure_time
			norm_update_time = update_time - arrival_time

			ratio = norm_shape_dist_trv / self.distance
			estimated_time_progress = time_diff * ratio
			return norm_update_time - estimated_time_progress

		def predict_standard(self, norm_shape_dist_trv, update_time):
			pass


		def get_name(self):
			return "Linear"


	class Polynomial_model(Super_model):

		def __init__(self, distance, norm_data: Norm_data):
			self.norm_data = norm_data
			self.distance = distance
			self.min_day_time = min(self.norm_data.get_day_times())
			self.max_day_time = max(self.norm_data.get_day_times())
			self._train_model()

		def _train_model(self):
			input_data = np.array([self.norm_data.get_shapes(), self.norm_data.get_day_times()]).transpose()
			input_data = np.pad(input_data, ((0, 0), (0, 1)), constant_values=1)

			output_data = np.array(self.norm_data.get_coor_times())

			X_train, X_test, y_train, y_test = train_test_split(input_data, output_data, test_size=0.33, random_state=42)

			best_degree = 3
			best_error = float('inf')  # maxint

			for degree in [3, 4, 5, 6, 7, 8, 9, 10]:
				model = make_pipeline(PolynomialFeatures(degree), Ridge())
				model.fit(X_train, y_train)
				pred = model.predict(X_test)
				error = mean_squared_error(y_test, pred)
				if error < best_error:
					best_degree = degree
					best_error = error
				# print("Deg:", degree, "Err", error)

			self.model = make_pipeline(PolynomialFeatures(best_degree), Ridge())
			self.model.fit(input_data, output_data)
			pred = self.model.predict(input_data)
			self.rmse = mean_squared_error(output_data, pred)

		def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
			if self.max_day_time < update_time:  # if in estimator area
				update_time = self.max_day_time

			if self.min_day_time > update_time:
				update_time = self.min_day_time

			time_diff = arrival_time - departure_time
			norm_update_time = update_time - departure_time

			input_data = np.pad(np.array([norm_shape_dist_trv, update_time]).T, ((0, 0), (0, 1)), constant_values=1)
			prediction = self.model.predict(input_data)  # estimation of coor time
			arrival_data = np.pad(np.array([self.distance, arrival_time]).T, ((0, 0), (0, 1)), constant_values=1)
			model_delay = self.model.predict(arrival_data) - time_diff  # no of seconds difference between scheduled arrival and model estimation
			return model_delay + norm_update_time - prediction

		def predict_standard(self, norm_shape_dist_trv, update_time):
			input_data = np.pad(np.array([norm_shape_dist_trv, update_time]).T, ((0, 0), (0, 1)), constant_values=1)
			return self.model.predict(input_data)

		def get_rmse(self):
			return self.rmse

		def get_name(self):
			return "Poly"

	class Concave_hull_model(Super_model):

		def has_enough_data(self):
			pass

		def predict_standard(self, norm_shape_dist_trv, update_time):
			pass

		def predict(self, norm_shape_dist_trv, update_time, departure_time, arrival_time):
			pass

		def get_name(self):
			return "Hull"



	# norm_data is dict of shapes, coor_times ands day_times, ids_trip
	def __init__(self, dep_id_stop: str, arr_id_stop: str, distance: int, max_travel_time: int, shapes, coor_times, day_times, ids_trip):
		self.dep_id_stop = dep_id_stop
		self.arr_id_stop = arr_id_stop
		self.distance = distance
		self.norm_data = Norm_data(shapes, coor_times, day_times, ids_trip)
		self.max_travel_time = max_travel_time
		self._create_model()

	def _reduce_errors(self):

		remove_alpha = 2
		trips_to_remove = set()
		for row in self.norm_data:
			if row.shape > self.distance - 200:  # 200 m to arrival stop
				if row.coor_times > self.max_travel_time * remove_alpha:
					trips_to_remove.add(row.ids_trip)

		self.norm_data.remove_items_by_id_trip(trips_to_remove)


	def _create_model(self):
		# linear -> < 2000 m, pocet dat alespon 10 na kilometr a 4 spoje denne
		self._reduce_errors()
		poly_model = Two_stops_model.Polynomial_model(self.distance, self.norm_data)
		rmse_aplha = 0.2
		print("rmse:", poly_model.get_rmse(), "dist * alpha:", self.distance * rmse_aplha)

		if self.distance < 2000:
			self.model = Two_stops_model.Polynomial_model(self.distance, self.norm_data)
			print("less than 2 km")
		elif len(self.norm_data) < self.distance * 0.0001 * 9 * 4: # 9 samples per km, 4 times a day
			self.model = Two_stops_model.Polynomial_model(self.distance, self.norm_data)
			print("not enough data")
		else:
			# poly_model = Two_stops_model.Polynomial_model(self.distance, self.norm_data)

			if poly_model.get_rmse() < self.distance * rmse_aplha:
				self.model = poly_model
			else:
				self.model = Two_stops_model.Concave_hull_model()

	def get_model(self) -> Super_model:
		return self.model
