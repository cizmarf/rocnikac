SELECT trips.trip_source_id, rides.id_stop, rides.shape_dist_traveled, arrival_time, departure_time
FROM trips  JOIN rides ON trips.id_trip=rides.id_trip
ORDER BY trips.trip_source_id, shape_dist_traveled;

SELECT * FROM headsigns where headsign = 'test';

CALL get_all_pairs_of_stops()