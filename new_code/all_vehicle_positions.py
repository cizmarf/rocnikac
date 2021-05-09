import glob
import json
import os
from os.path import getmtime

from file_system import File_system
from network import Network
from trip import Trip

class Static_all_vehicle_positions:

	def __init__(self, args):
		sufix = ''
		if args.thu_only:
			sufix = '/2020-02-20*.tar.gz'
		else:
			sufix = '/*.tar.gz'

		sufix = '/2020-02-2[01]*.tar.gz'

		self.files = glob.glob(str(File_system.static_vehicle_positions) + sufix)
		self.files = sorted(self.files)

	def static_get_all_vehicle_positions_json(self):

		for file in self.files:
			content = File_system.get_tar_file_content(file)

			json_file = json.loads(content)
			json_file['name'] = file
			yield json_file



class All_vehicle_positions():

	# Function to find first occurrence of a given number
	# in sorted list of integers
	# function code is inspired from the internet
	@staticmethod
	def findFirstOccurrence(A, x):
		# search space is A[left..right]
		(left, right) = (0, len(A) - 1)

		# get sort order
		order = 'asc'
		if A[0] > A[len(A) - 1]:
			order = 'des'

		# initialize the result by -1
		result = -1

		# iterate till search space contains at-least one element
		while left <= right:

			# find the mid value in the search space and
			# compares it with key value
			mid = (left + right) // 2

			# if key is found, update the result and
			# go on searching towards left (lefter indices)
			if x == A[mid]:
				result = mid
				right = mid - 1

			elif order == 'asc':
				# if key is less than the mid element, discard right half
				if x < A[mid]:
					right = mid - 1
				# if key is more than the mid element, discard left half
				else:
					left = mid + 1
			else:
				if x > A[mid]:
					right = mid - 1
				else:
					left = mid + 1

		# return the leftmost index or -1 if the element is not found
		return result

	@staticmethod
	def get_sublist(A, indexA, indexB):
		return A[indexA:indexB]

	# linear search, number of stops use to be up to 100
	# if shape dist trav is out of range it keeps nones for last and next stop
	@staticmethod
	def get_last_next_stop_and_sdt(trip_ride, shape_traveled):
		for i in range(len(trip_ride) - 1):
			if trip_ride[i][2] <= shape_traveled < trip_ride[i + 1][2]:
				# trip.last_stop, trip.next_stop, trip.last_stop_shape_dist_trav, trip.departure_time, trip.arrival_time, trip.stop_dist_diff
				return trip_ride[i][1], trip_ride[i + 1][1], trip_ride[i][2], trip_ride[i][4], trip_ride[i + 1][3], trip_ride[i + 1][2] - trip_ride[i][2]

		return None, None, None, None, None, None

	def __init__(self):
		self.json_file = dict()
		self.vehicles = list()


	def iterate_vehicles(self):
		try:
			for vehicle in self.vehicles:
				yield vehicle
		except KeyError as e:
			print("no feature")
			return None


	def get_all_vehicle_positions_json(self):
		self.json_file = Network.download_URL_to_json(Network.vehicles_positions)

	# finds ride for given trip id
	@staticmethod
	def get_trip_rides_sublist(trip_rides, trip_ids, trip_id):
		return All_vehicle_positions.get_sublist(trip_rides,
					All_vehicle_positions.findFirstOccurrence(
						trip_ids, trip_id),
					len(trip_ids) - All_vehicle_positions.findFirstOccurrence(
						trip_ids[::-1], trip_id))


	def construct_all_trips(self, database_connection):
		try:
			# finds ids of all current trips
			trip_ids = []
			for vehicle in self.json_file["features"]:
				trip_ids.append(vehicle["properties"]["trip"]["gtfs_trip_id"])

			# selects timetables of these trips
			# for getting last and next stop by shape dist traveled
			trip_rides = database_connection.execute_fetchall(
				"""	SELECT 
						trips.trip_source_id, 
						rides.id_stop, 
						rides.shape_dist_traveled,
						rides.arrival_time,
						rides.departure_time
					FROM trips 
					JOIN rides ON trips.id_trip=rides.id_trip 
					WHERE trips.trip_source_id IN ({seq}) 
					ORDER BY trips.trip_source_id, shape_dist_traveled""".format(
    					seq=','.join(['%s']*len(trip_ids))
				), trip_ids)

			if len(trip_rides) > 0:
				# gets ids only for easy find array indices of current trip
				trip_ids = list(zip(*trip_rides))[0]

			for vehicle in self.json_file["features"]:
				trip = Trip()
				trip.set_attributes_by_vehicle(vehicle)

				if len(trip_rides) > 0:
					# gets sublist of trips rides for current trip
					# by looking for first and last occurrence of trip id
					trip_ride = All_vehicle_positions.get_trip_rides_sublist(
						trip_rides, trip_ids, trip.trip_id)

					trip.last_stop, \
					trip.next_stop, \
					trip.last_stop_shape_dist_trav, \
					trip.departure_time, \
					trip.arrival_time, \
					trip.stop_dist_diff = \
						All_vehicle_positions.get_last_next_stop_and_sdt(
							trip_ride, trip.shape_traveled)

				if trip.last_stop_delay is not None and trip.cur_delay is not None:
					self.vehicles.append(trip)
		except KeyError:
			print("error")

	def get_trip_source_id_by_vehicle(self, vehicle) -> str:
		return vehicle.trip_id
