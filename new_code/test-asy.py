import glob
import json
import re
from os.path import getmtime

from file_system import File_system


class A:
	def __init__(self):
		# path = str(File_system.static_vehicle_positions) + "*.tar.gz"
		self.files = glob.glob(str(File_system.static_vehicle_positions) + "/*.tar.gz")
		self.files.sort(key=getmtime)


	def static_get_all_vehicle_positions_json(self):
		for file in self.files:
			content = File_system.get_tar_file_content(file)

			json_file = content.decode("utf-8")
			# print("file: " + file)
			yield json_file

a = A()

for f in a.static_get_all_vehicle_positions_json():
	if re.search("421_225_191114", f):
		print("line: " + f)
		exit(0)