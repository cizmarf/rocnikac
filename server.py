import argparse
import logging
import threading
import webbrowser
from wsgiref.simple_server import make_server
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from common_functions import allFilesURL, Log


class Veh_pos_file_handler(FileSystemEventHandler):

	def on_modified(self, event):
		try:
			with open(allFilesURL.vehicles_positions, 'r') as f:
				if f.mode == 'r':
					self.veh_pos_file_content = f.read()
		except IOError as e:
			logging.warning("IOE " + e)

	def __init__(self):
		self.veh_pos_file_content = ""
		self.on_modified(None)

FILE = 'index.html'
PORT = 8080

def server(environ, start_response):

	if environ['REQUEST_METHOD'] == 'POST':
		try:
			request_body_size = int(environ['CONTENT_LENGTH'])
			request_body = environ['wsgi.input'].read(request_body_size)
		except (TypeError, ValueError):
			request_body = None

		response_body = ""
		request_body = request_body.decode('utf-8')
		if request_body == "vehicles_positions":
			response_body = event_handler.veh_pos_file_content

		status = '200 OK'
		headers = [('Content-type', 'text/plain')]
		start_response(status, headers)
		return [response_body.encode()]
	else:
		response_body = open(FILE).read()
		status = '200 OK'
		headers = [('Content-type', 'text/html'),
				   ('Content-Length', str(len(response_body)))]
		start_response(status, headers)
		return [response_body.encode()]

def start_server():
	"""Start the server."""
	httpd = make_server("", PORT, server)
	httpd.serve_forever()




if __name__ == "__main__":
	logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename=allFilesURL.log_server, filemode='w')
	logging.info(Log.start)
	event_handler = Veh_pos_file_handler()
	observer = Observer()
	observer.schedule(event_handler, path=allFilesURL.vehicles_positions, recursive=False)
	observer.start()
	start_server()
