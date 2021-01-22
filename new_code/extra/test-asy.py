import glob
import json
import re
from datetime import datetime
from os.path import getmtime
from urllib.parse import quote
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from file_system import File_system


def load_idos():

	url = 'https://idos.idnes.cz/vlakyautobusy/spojeni/vysledky/?date=15.09.2020&time=07:00&f=Praha&fc=1&t=Liberec&tc=1'

	request = Request(url)
	webURL = urlopen(request)
	connections_distances = []
	connections_times = []

	soup = None

	if 200 <= webURL.getcode() < 400:
		response_body = webURL.read()
		encoding = webURL.info().get_content_charset('utf-8')
		soup = BeautifulSoup(response_body.decode(encoding), features="html.parser")

	else:
		raise IOError('IDOS does not load for URL:', url)

	webURL.close()

	try:
		connection_box_regex = re.compile('connectionBox-[0-9]+')
		connections = soup.find_all(id=connection_box_regex)

		if len(connections) == 0:
			raise IOError('Not enough connections')

		for connection in connections:
			try:
				time = connection.div.div.label.p.strong.getText()
				distance = connection.div.div.label
				distance = distance.p.find_all('strong')[1].getText()

				connections_distances.append(int(re.search(r'([0-9]+) km', distance).group(1)))

				total_seconds = 0
				hours = re.search(r'([0-9]+) hod', time)
				minutes = re.search(r'([0-9]+) min', time)

				if bool(hours):
					total_seconds += int(hours.group(1)) * 60 * 60

				if bool(minutes):
					total_seconds += int(minutes.group(1)) * 60

				connections_times.append(total_seconds)

			except IndexError as e:
				print('Bad formatted connection box for stops:', url)

		connections = [str(con) for con in connections]



	except (IOError, IndexError) as e:
		print('Bad formatted HTML for stops:', url)

load_idos()