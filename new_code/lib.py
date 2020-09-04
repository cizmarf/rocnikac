## support functions library for vehicles delay prediction project

from datetime import datetime

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
	return timed.time().hour * SECONDS_AN_HOUR + timed.time().minute * MINUTES_AN_HOUR + timed.time().second  # + 3600