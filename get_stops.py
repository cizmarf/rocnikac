from urllib.request import Request, urlopen
import sys;

headers = {
  'Content-Type': 'application/json; charset=utf-8',
  'x-access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNpem1hcmZpbGlwQGdtYWlsLmNvbSIsImlkIjo3NiwibmFtZSI6bnVsbCwic3VybmFtZSI6bnVsbCwiaWF0IjoxNTcwNTQ2MTU2LCJleHAiOjExNTcwNTQ2MTU2LCJpc3MiOiJnb2xlbWlvIiwianRpIjoiMzAxYWNhNDUtNGRlNC00ZDRmLWI4NzAtMzQwMDQ5OTM1MzBhIn0.4rCELzCNY8XOSvjqQA7cKocPGJ8D2ezhXiWUkIRUNjg'
}

parameters = ""
if len(sys.argv) > 1:
	parameters = '?' + sys.argv[1]

request = Request('https://api.golemio.cz/v1/gtfs/stops' + parameters, headers=headers)

response_body = urlopen(request).read()
print(response_body)
