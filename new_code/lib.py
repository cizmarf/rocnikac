## support functions library for vehicles delay prediction project

from datetime import datetime


from all_vehicle_positions import All_vehicle_positions
from two_stops_model import Two_stops_model

## Constants
MINUTES_AN_HOUR = 60
SECONDS_AN_HOUR = 3600


def is_business_day(date):
	# if isinstance(date, str):
	# 	date = datetime(date)
	day_of_week = date.weekday()
	if 0 <= day_of_week < 5:
		return True
	return False


def time_to_sec(timed):
	return timed.time().hour * SECONDS_AN_HOUR + \
		   timed.time().minute * MINUTES_AN_HOUR + \
		   timed.time().second


def estimate_delays(all_vehicle_positions: All_vehicle_positions, models):

	for vehicle in all_vehicle_positions.iterate_vehicles():

		# gets model from given set, if no model found uses linear model by default
		model = models.get(
			str(vehicle.last_stop or '') + "_" +
			str(vehicle.next_stop or '') +
			("_bss" if is_business_day(vehicle.last_updated) else "_hol"),
			Two_stops_model.Linear_model(vehicle.stop_dist_diff))

		tuple_for_predict = vehicle.get_tuple_for_predict()

		# else it uses last stop delay, set in trips construction
		if tuple_for_predict is not None:
			vehicle.cur_delay = model.predict(*tuple_for_predict)
