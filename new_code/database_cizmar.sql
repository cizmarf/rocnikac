CREATE DATABASE `vehicle_positions_database`;

-- SET @@global.time_zone = '+00:00';

CREATE TABLE `vehicle_positions_database`.`stops` (
  `id_stop` INT(32) NOT NULL AUTO_INCREMENT,
  `stop_source_id` VARCHAR(31) NOT NULL COMMENT 'ID used in golemio API',
  `parent_id_stop` INT(32) NULL,
  `stop_name` VARCHAR(123) NOT NULL,
  `lat` DECIMAL(9,6) NOT NULL,
  `lon` DECIMAL(9,6) NOT NULL,
  PRIMARY KEY (`id_stop`),
  INDEX `parent_id_stop_x` (`parent_id_stop` ASC) VISIBLE,
  INDEX `stop_parent_id_spot_x` (`parent_id_stop` ASC) VISIBLE,
  INDEX `stop_name_x` (`stop_name` ASC) VISIBLE,
  UNIQUE INDEX `stop_source_id_UNIQUE` (`stop_source_id` ASC) VISIBLE
);


ALTER TABLE `vehicle_positions_database`.`stops`
  ADD CONSTRAINT `parent_stop`
    FOREIGN KEY (`parent_id_stop`)
    REFERENCES `vehicle_positions_database`.`stops` (`id_stop`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION;
;


CREATE TABLE `vehicle_positions_database`.`headsigns` (
  `id_headsign` INT(32) NOT NULL AUTO_INCREMENT,
  `headsign` VARCHAR(123) NOT NULL,
  PRIMARY KEY (`id_headsign`),
  UNIQUE INDEX `headsign_UNIQUE` (`headsign` ASC) VISIBLE
);


CREATE TABLE `vehicle_positions_database`.`trips` (
  `id_trip` INT(32) NOT NULL AUTO_INCREMENT,
  `trip_source_id` VARCHAR(31) NOT NULL COMMENT 'ID used in golemio API',
  `id_headsign` INT(32) NOT NULL COMMENT 'Link into headsigns table',
  `current_delay` INT(32) NOT NULL,
  `shape_dist_traveled` INT(32) NOT NULL,
  `last_updated` DATETIME NOT NULL, -- DEFAULT NOW() ON UPDATE CURRENT_TIMESTAMP, COMMENT 'Time of last change or insertirion of a row'
  `trip_no` VARCHAR(7) NOT NULL COMMENT 'Unique number for a bus line.',
  PRIMARY KEY (`id_trip`),
  UNIQUE INDEX `id_trip_UNIQUE` (`id_trip` ASC) VISIBLE,
  INDEX `id_headsign_x` (`id_headsign` ASC) VISIBLE,
  UNIQUE INDEX `trip_source_id_x` (`trip_source_id` ASC) VISIBLE,
  CONSTRAINT `id_headsign_from_trips_to_headsigns`
	FOREIGN KEY (`id_headsign`)
	REFERENCES `vehicle_positions_database`.`headsigns` (`id_headsign`)
	ON DELETE CASCADE
  	ON UPDATE NO ACTION
);


CREATE TABLE `vehicle_positions_database`.`rides` (
  `id_trip` INT(32) NOT NULL,
  `id_stop` INT(32) NOT NULL,
  `arrival_time` TIME NOT NULL,
  `departure_time` TIME NOT NULL,
  `shape_dist_traveled` INT(32) NOT NULL,
  INDEX `id_trip_x` (`id_trip` ASC) VISIBLE,
  INDEX `shape_dist_traveled_x` (`shape_dist_traveled` ASC) VISIBLE,
  CONSTRAINT `id_trip_from_rides_to_trips`
    FOREIGN KEY (`id_trip`)
    REFERENCES `vehicle_positions_database`.`trips` (`id_trip`)
    ON DELETE CASCADE,
  CONSTRAINT `id_stop_from_rides_to_stops`
      FOREIGN KEY (`id_stop`)
      REFERENCES `vehicle_positions_database`.`stops` (`id_stop`)
      ON DELETE CASCADE
  );


  CREATE TABLE `vehicle_positions_database`.`trip_coordinates` (
      `id_trip` INT(32) NOT NULL,
      `lat` DECIMAL(9,6) NOT NULL,
      `lon` DECIMAL(9,6) NOT NULL,
      `inserted` DATETIME NOT NULL,
      `delay` INT(32) NOT NULL,
      `shape_dist_traveled` INT(32) NOT NULL,
  	INDEX `id_trip_x` (`id_trip` ASC) VISIBLE,
  	INDEX `shape_dist_traveled_x` (`shape_dist_traveled` ASC) VISIBLE,
  	CONSTRAINT `id_trip_from_trip_coordinates_to_trips`
  	  FOREIGN KEY (`id_trip`)
  	  REFERENCES `vehicle_positions_database`.`trips` (`id_trip`)
  	  ON DELETE CASCADE
  );


-- shows trips with its headsigns instend of headsigns internal id
USE `vehicle_positions_database`;
CREATE OR REPLACE VIEW `trip_number_on_headsign` AS
	SELECT trips.trip_no, headsigns.headsign
	FROM trips
	INNER JOIN headsigns ON trips.id_headsign = headsigns.id_headsign;


CREATE DEFINER=`root`@`localhost` FUNCTION `insert_headsign_if_exists_and_return_id` (headsign_to_insert VARCHAR(123))
RETURNS INTEGER
DETERMINISTIC
BEGIN
	INSERT IGNORE INTO headsigns (headsign)
	VALUES (headsign_to_insert);

    SELECT id_headsign
    INTO @id
    FROM headsigns
    WHERE headsign = headsign_to_insert;

    RETURN @id;
END;


-- if a new trip found it inserts headsign if not exists, create new trip record and insert current location data into historical data table
-- deprecated
CREATE DEFINER=`root`@`localhost` FUNCTION `insert_new_trip_to_trips_and_coordinates_and_return_id`(
	trip_source_id_to_insert VARCHAR(31),
	headsign_to_insert VARCHAR(123),
	current_delay_to_insert INT(32),
	shape_dist_traveled_to_insert INT(32),
	trip_no_to_insert VARCHAR(7),
	last_updated_to_insert DATETIME,
	lat_to_insert DECIMAL(9,6),
	lon_to_insert DECIMAL(9,6)
)
RETURNS int(32)
DETERMINISTIC

BEGIN
	INSERT IGNORE INTO headsigns(headsign)
		VALUES (headsign_to_insert);

    SELECT id_headsign
    INTO @id_headsign_to_insert
    FROM headsigns
    WHERE headsign = headsign_to_insert
    LIMIT 1;

	INSERT INTO trips (
	    trip_source_id,
	    id_headsign,
	    current_delay,
	    shape_dist_traveled,
	    trip_no,
        last_updated)
	VALUES (
        trip_source_id_to_insert,
        @id_headsign_to_insert,
        current_delay_to_insert,
        shape_dist_traveled_to_insert,
        trip_no_to_insert,
        last_updated_to_insert);

    SELECT LAST_INSERT_ID()
    INTO @id_trip;

    INSERT INTO trip_coordinates (
        id_trip,
        lat,
        lon,
        inserted,
        delay,
        shape_dist_traveled)
	VALUES (@id_trip,
	        lat_to_insert,
	        lon_to_insert,
	        last_updated_to_insert,
	        current_delay_to_insert,
	        shape_dist_traveled_to_insert);

    RETURN @id_trip;
END;

-- inserts a stop if does not exist and return its id anyway
CREATE DEFINER=`root`@`localhost` FUNCTION `insert_stop_if_exists_and_return_id`(
stop_source_id_to_insert VARCHAR(31),
stop_name_to_insert VARCHAR(123),
lat_to_insert DECIMAL(9, 6),
lon_to_insert DECIMAL(9, 6),
parent_id_stop_to_insert INT(32)
)
RETURNS INT(32)
DETERMINISTIC

BEGIN
	INSERT IGNORE INTO stops (stop_source_id, stop_name, lat, lon, parent_id_stop)
		VALUES (
		        stop_source_id_to_insert,
		        stop_name_to_insert,
		        lat_to_insert,
		        lon_to_insert,
		        parent_id_stop_to_insert);

    SELECT id_stop INTO @id FROM stops WHERE stop_source_id = stop_source_id_to_insert;

    RETURN @id;
END;


-- select shape distance traveled of given trip and then it select all stops from rides table of the trip whose shape distance traveled is less than current trip shape distance traveled, returns id of first stop order by shape distance traveled
CREATE DEFINER=`root`@`localhost` FUNCTION `last_passed_id_stop_of_trip` (id_trip_to_find INT(32))
RETURNS INT(32)
DETERMINISTIC

BEGIN
	DECLARE id_stop_to_find INT(32);

	SET id_stop_to_find = 0;

	SELECT id_stop
	INTO id_stop_to_find
	FROM rides
	WHERE shape_dist_traveled <= (
		SELECT `shape_dist_traveled`
		FROM trips
		WHERE id_trip = id_trip_to_find
		LIMIT 1
	)
	AND id_trip_to_find = id_trip
	ORDER BY shape_dist_traveled
	DESC LIMIT 1;

 RETURN id_stop_to_find;
END;


CREATE PROCEDURE `delete_trips_older_than_and_return_their_trip_id` (period_minutes INT(32))
BEGIN
	DECLARE period DATETIME;

	SET period = 0;

    SELECT (NOW() - INTERVAL period_minutes MINUTE)
    INTO period;

    SELECT trip_source_id
    FROM trips
    WHERE last_updated < period;

	DELETE FROM trips
	WHERE last_updated < period;
END;


-- returns all pairs of stops where the first is right followed by the second in ride of at least one trip
-- for each pair it selects all trip coordinates data captured between these stops
CREATE PROCEDURE `get_all_pairs_of_stops` ()
BEGIN
    SELECT schedule.id_trip,
        schedule.id_stop,
        schedule.lead_stop,
        departure_time,
        schedule.lead_stop_departure_time,
        (schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled)
            AS diff_shape_trav,
        trip_coordinates.inserted,
        (trip_coordinates.shape_dist_traveled - schedule.shape_dist_traveled)
            AS shifted_shape_trav,
        trip_coordinates.delay
    FROM (
        SELECT id_trip, id_stop, shape_dist_traveled, departure_time,
            LEAD(id_stop, 1) OVER (
                PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop,
            LEAD(shape_dist_traveled, 1) OVER (
                PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_shape_dist_traveled,
            LEAD(departure_time, 1) OVER (
                PARTITION BY id_trip ORDER BY shape_dist_traveled) lead_stop_departure_time
        FROM rides) AS schedule
    JOIN trip_coordinates
    ON trip_coordinates.id_trip = schedule.id_trip AND
        schedule.lead_stop_shape_dist_traveled - schedule.shape_dist_traveled > 1500 AND
        trip_coordinates.shape_dist_traveled BETWEEN schedule.shape_dist_traveled AND
        schedule.lead_stop_shape_dist_traveled
    ORDER BY id_stop, lead_stop, shifted_shape_trav;
END;





CREATE DEFINER=`root`@`localhost` FUNCTION `update_trip_and_insert_coordinates_if_changed`(
	trip_source_id_to_insert VARCHAR(31),
	current_delay_to_insert INT(32),
    last_stop_delay INT(32),
	shape_dist_traveled_to_insert INT(32),
	lat_to_insert DECIMAL(9,6),
	lon_to_insert DECIMAL(9,6),
	last_updated_to_insert DATETIME)
RETURNS int(1)
DETERMINISTIC
BEGIN
	SELECT last_updated, id_trip
	INTO @last_updated, @id_trip
	FROM trips
	WHERE trips.trip_source_id = trip_source_id_to_insert
	LIMIT 1;

	IF @last_updated <> last_updated_to_insert THEN
		INSERT INTO trip_coordinates (
		    id_trip,
		    lat,
		    lon,
		    inserted,
		    delay,
		    shape_dist_traveled)
		VALUES (
		    @id_trip,
		    lat_to_insert,
		    lon_to_insert,
		    last_updated_to_insert,
		    last_stop_delay,
		    shape_dist_traveled_to_insert);
		UPDATE trips
		SET trips.last_updated = last_updated_to_insert,
		    trips.current_delay = current_delay_to_insert,
		    trips.shape_dist_traveled = shape_dist_traveled_to_insert
		WHERE trips.id_trip = @id_trip;
        RETURN 1;
	ELSE
		RETURN 0;
	END IF;
END