import math
import unittest

import matplotlib.pyplot as plt
import numpy as np


class TestGeneratePlots(unittest.TestCase):

	def test_trips_processing_time(self):
		with open("../input_data/fill_database_output_seconds", "r") as file:
			map = {}
			line = file.readline()
			while line != '':
				if 'vehicles processed' in line:
					no_of_vehicles = math.floor(int(line.split()[0]) / 10.0) * 10
					time = float(line.split()[4])
					if no_of_vehicles in map:
						map[no_of_vehicles].append(time)
					else:
						map[no_of_vehicles] = [time]
				line = file.readline()

			plt.figure(figsize=(10, 8))
			plt.subplot()
			sorted_map = sorted(map)
			ci = np.array([1.96 * np.std(np.array(map[k])) / math.sqrt(len(map[k])) for k in sorted_map])
			y = np.array([np.mean(np.array(map[k])) for k in sorted_map])
			plt.plot(sorted_map, y, label='Průměr')
			plt.fill_between(sorted_map, (y - ci), (y + ci), color='b', alpha=.1, label='95% interval spolehlivosti')

			# self.assertEqual(sum([v[1] for v in sorted_map]), 15793)
			# plt.title('Průměrný čas zpracování daného počtu vozidel s 95 % intervalem spolehlivosti.')
			plt.xlabel('Počet vozidel')
			plt.ylabel('Čas [s]')
			# plt.yscale('log')
			plt.legend(loc='upper left')
			plt.savefig('file_process_time.pdf')
			plt.show()

if __name__ == '__main__':
	unittest.main()
