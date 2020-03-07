#!/bin/sh

cur_file="current_json_file.json";
while :
do
	curl -s --header "Content-Type: application/json; charset=utf-8" \
	--header "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNpem1hcmZpbGlwQGdtYWlsLmNvbSIsImlkIjo3NiwibmFtZSI6bnVsbCwic3VybmFtZSI6bnVsbCwiaWF0IjoxNTcwNTQ2MTU2LCJleHAiOjExNTcwNTQ2MTU2LCJpc3MiOiJnb2xlbWlvIiwianRpIjoiMzAxYWNhNDUtNGRlNC00ZDRmLWI4NzAtMzQwMDQ5OTM1MzBhIn0.4rCELzCNY8XOSvjqQA7cKocPGJ8D2ezhXiWUkIRUNjg" \
	'https://api.golemio.cz/v1/vehiclepositions' > "$cur_file";

	if [ 0 -ne $? ];
	then
		today=`date +%Y-%m-%dT%H.%M.%S`;
		echo "Curl failed $today" >> downloader.log;
		sleep 19;
		continue;

	fi

	today=`date +%Y-%m-%dT%H.%M.%S`;

	tar -czf "../raw_data-2/${today}.tar.gz" $cur_file;
	
	echo "File ${today}.tar.gz saved." >> downloader.log
	
	sleep 19

done
