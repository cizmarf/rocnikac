import lzma
import os
import pickle
import tarfile
from io import BytesIO

import json
from pathlib import Path


class File_system:

	# specify your absolute path here
	cwd = Path("/Users/filipcizmar/Documents/rocnikac/rocnikac_source/new_code/")

	static_vehicle_positions = 	cwd / Path("tests/input_data/raw_vehicle_positions_all/")
	static_trips = 				cwd / Path("data/raw_trips/")
	all_shapes = 				cwd / Path("data/shapes/")
	all_models = 				cwd / Path("data/models/")

	# deprecate
	# all_vehicle_positions_real_time_geojson = cwd / Path("data/vehicle_positions/vehicle_positions.json")


	@staticmethod
	def get_tar_file_content(path) ->bytes:
		with tarfile.open(path, "r:gz") as tar:
			print("cur file:", path)
			member = tar.getmembers()[0]
			f = tar.extractfile(member)
			if f is not None:
				return f.read()
			else:
				return b""


	@staticmethod
	def save_tar_file(content: dict, path, name):
		path_name = ""
		if isinstance(path, Path):
			path_name = path.joinpath(name)
		elif isinstance(name, Path):
			path_name = Path(path).joinpath(name)
		else:
			path_name = path + name

		with tarfile.open(path_name, "w:gz") as tar_out:
			string = BytesIO(json.dumps(content).encode())
			string.seek(0)
			info = tarfile.TarInfo(name=str(name))
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
		try:
			with open(path, "r") as f:
				if f is not None:
					return f.read()
				else:
					return ""
		except FileNotFoundError:
			return ""


	@staticmethod
	def delete_file(path):
		try:
			os.remove(path)
		except Exception as e:
			print("file not found", path)


	@staticmethod
	def load_all_models() -> dict:
		models = {}
		# models_path = [join(File_system.all_models, f) for f in listdir(File_system.all_models) if isfile(join(File_system.all_models, f))]
		models_path = [path for path in Path(File_system.all_models).glob('*.model')
					   if path.is_file()]

		for model_path in models_path:
			with lzma.open(model_path, "rb") as model_file:
				models[model_path.stem] = pickle.load(model_file)

		return models


	@staticmethod
	def pickle_object(obj, path):
		with lzma.open(path, "wb") as file:
			pickle.dump(obj, file)


	@staticmethod
	def pickle_load_object(path):
		with lzma.open(path, "rb") as file:
			return pickle.load(file)
