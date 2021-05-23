import json
import os
import unittest
from pathlib import Path

from file_system import File_system

class TestFile_system(unittest.TestCase):
	def test_get_tar_file_content_get_file_content(self):
		tar_file = File_system.get_tar_file_content("../input_data/2020-02-20T13.50.23.tar.gz").decode('utf-8')
		json_file = File_system.get_file_content("../input_data/2020-02-20T13.50.23.json")

		self.assertEqual(tar_file, json_file)

	def test_save_tar_file(self):
		json_dict = json.loads(File_system.get_file_content("../input_data/2020-02-20T13.50.23.json"))
		File_system.save_tar_file(json_dict, "../output_data/", "tmp.tar.gz")

		json_tar = json.loads(File_system.get_tar_file_content("../output_data/tmp.tar.gz"))
		File_system.delete_file("../output_data/tmp.tar.gz")

		self.assertEqual(json_dict, json_tar)

	def test_save_tar_filePath(self):
		json_dict = json.loads(File_system.get_file_content(Path("../input_data/2020-02-20T13.50.23.json")))
		File_system.save_tar_file(json_dict, Path("../output_data/"), Path("tmp.tar.gz"))

		json_tar = json.loads(File_system.get_tar_file_content(Path("../output_data/tmp.tar.gz")))
		File_system.delete_file("../output_data/tmp.tar.gz")

		self.assertEqual(json_dict, json_tar)

	def test_save_file(self):
		json_dict = json.loads(File_system.get_file_content(Path("../input_data/2020-02-20T13.50.23.json")))
		File_system.save_file(json_dict, "../output_data/tmp.json")

		tmp_json = json.loads(File_system.get_file_content("../output_data/tmp.json"))
		File_system.delete_file("../output_data/tmp.json")

		self.assertEqual(json_dict, tmp_json)

	def test_delete_file(self):
		File_system.save_file({"test": "val"}, "../output_data/tmp.json")
		File_system.delete_file("../output_data/tmp.json")
		self.assertEqual(File_system.get_file_content("../output_data/tmp.json"), "")

	def test_load_all_models(self):
		models = File_system.load_all_models()

		from two_stops_model import Two_stops_model

		for model in models.values():
			assert isinstance(model, (Two_stops_model.Polynomial_model))

		self.assertGreater(len(models), 0)
		self.assertEqual(len(os.listdir(File_system.all_models)), len(models))

	def test_pickle_object_pickle_load_object(self):
		obj = ["hello", "world"]
		File_system.pickle_object(obj, "../output_data/tmp.pickle")
		tmp = File_system.pickle_load_object(Path("../output_data/tmp.pickle"))

		File_system.delete_file(Path("../output_data/tmp.pickle"))

		self.assertEqual(obj, tmp)

if __name__ == '__main__':
	unittest.main()
