from urllib.request import Request, urlopen
import time
import zlib, json, base64

ZIPJSON_KEY = 'base64(zip(o))'


def json_zip(j):

    j = {
        ZIPJSON_KEY: base64.b64encode(
            zlib.compress(
                json.dumps(j).encode('utf-8')
            )
        ).decode('ascii')
    }

    return j


headers = {
	'Content-Type': 'application/json; charset=utf-8',
	'x-access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNpem1hcmZpbGlwQGdtYWlsLmNvbSIsImlkIjo3NiwibmFtZSI6bnVsbCwic3VybmFtZSI6bnVsbCwiaWF0IjoxNTcwNTQ2MTU2LCJleHAiOjExNTcwNTQ2MTU2LCJpc3MiOiJnb2xlbWlvIiwianRpIjoiMzAxYWNhNDUtNGRlNC00ZDRmLWI4NzAtMzQwMDQ5OTM1MzBhIn0.4rCELzCNY8XOSvjqQA7cKocPGJ8D2ezhXiWUkIRUNjg'
}
request = Request('https://api.golemio.cz/v1/vehiclepositions', headers=headers)
target_folder = 'positions_history'
while True:
	req_start = time.time()
	webURL = urlopen(request)
	response_body = webURL.read()
	encoding = webURL.info().get_content_charset('utf-8')
	json_data = json.loads(response_body.decode(encoding))
	timestr = time.strftime("%Y-%m-%d-%H:%M:%S")
	with open(target_folder + '/' + timestr + '.json', 'w+') as f:
		ziped = json_zip(json_data)
		dump = json.dumps(ziped)
		f.write(dump)
		f.close()
		time.sleep(20 - (time.time() - req_start))
