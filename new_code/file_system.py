import lzma
import ntpath
import os
import pickle
import tarfile
from io import BytesIO

import json
from os import listdir
from os.path import isfile, join
from pathlib import Path


class File_system:

	static_vehicle_positions = Path("/Users/filipcizmar/Documents/rocnikac/raw_data_test/")
	static_trips = Path("/Users/filipcizmar/Documents/rocnikac/raw-trips/")
	all_shapes = Path("/Users/filipcizmar/Documents/rocnikac/data/trips/")
	all_vehicle_positions_real_time_geojson = Path("/Users/filipcizmar/Documents/rocnikac/data/vehicle_positions")
	all_models = Path("/Users/filipcizmar/Documents/rocnikac/data/models")

	@staticmethod
	def get_tar_file_content(path) -> str:
		with tarfile.open(path, "r:gz") as tar:
			print("cur file:", path)
			member = tar.getmembers()[0]
			f = tar.extractfile(member)
			if f is not None:
				return f.read()
			else:
				return ""

	@staticmethod
	def save_tar_file(content: dict, path, name):
		with tarfile.open(path, "w:gz") as tar_out:
			string = BytesIO(json.dumps(content).encode())
			string.seek(0)
			info = tarfile.TarInfo(name=name)
			info.size = len(string.getvalue())
			tar_out.addfile(tarinfo=info, fileobj=string)


	@staticmethod
	def save_file(content: dict, path):
		try:
			with open(path, 'w+') as f:
				f.seek(0)
				f.write(json.dumps(content))

		except Exception as e:
			raise IOError(e)


	@staticmethod
	def get_file_content(path):
		pass

	@staticmethod
	def delete_file(path):
		try:
			os.remove(path)
		except Exception as e:
			print("file not found", path)

	@staticmethod
	def load_all_models():
		models = {}
		# models_path = [join(File_system.all_models, f) for f in listdir(File_system.all_models) if isfile(join(File_system.all_models, f))]
		models_path = [path for path in Path(File_system.all_models).glob('*') if path.is_file()]

		for model_path in models_path:
			with lzma.open(model_path, "rb") as model_file:
				models[model_path.stem] = pickle.load(model_file)

		return models

if __name__ == '__main__':
	print(File_system.load_all_models())
