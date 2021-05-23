## Analysis of real-time data of public transport vehicles

This thesis deals with analysis of real-time data of public transport vehicles over open data in Prague. Its main purpose is to create statistics and improve estimation, based on historical data, of a vehicle delay on its route be- tween reference points. For demonstration of the computed data a front-end web app is created. This interactive app is able to show current vehicles locations over a map and other useful information. All components were tested. Open data from Prague public transport company were used to demonstrate that open data can be used for achieving high goals.

### In Brief

Using this project we can download real-time vehicles positions and store them into the database. If we collected enough samples we can model profiles of rides of trips. These models can be used for future delay estimation. All the data can be visualized in a client app.

Read more in the attached [thesis](./Bakalarska_prace_Cizmar.pdf) in czech language.

### Prerequisites

Install Python 3.7, MySQL 8.0.18 database.

Python 3 source code uses some extra Python libraries. Out of the most common the required libraries are:

- scikit-learn -- https://scikit-learn.org/stable/
- NumPy -- https://numpy.org
- mysql.connector -- https://dev.mysql.com/doc/connector-python/en/
- ftfy -- https://pypi.org/project/ftfy/
- tarfile -- https://docs.python.org/3/library/tarfile.html

Read import part of all the source files to install other libraries.

To run the client app you must have working modern web browser. And if you want to see the live data you mush have an internet connection.


### Installation

Download this source code.

Set up the database using queries in [database.sql](./source/database.sql) file. You may create functions and procedures manually.

Set constants in [file_system.py](./source/file_system.py) file. Paths of models, trips shapes. And paths to static data.

If you want to use static datasets they are located in vehicle_positions and trips folders.

Create your own access token to Golemio data platform at [this link](https://api.golemio.cz/api-keys/auth/sign-in). And put it to [network.py](./source/network.py) line 10.

To make sure everything is working you can run tests in [tests](./source/tests) directory. The main function test fills database what usually takes a long time, don't run it if you are interested in live or static demo only.

### Demo

A [skript](./source/tests/integration/test_main.py) is located the integration tests folder. And it runs a simple demo. For this create a subset of static data or use live data. In case you use static data one function in client app may not work correctly. This function is a stop time table, it is cause by different time of insertion to database (always now) and timetable of passing trips.

If you want to see busses riding faster use option `update_time` to make them faster (works with static data only).

You don't need to use this test but you can run this demo from main function using right options.

Than you need to start the server app in [server.py](./source/server.py). Now you can open the [index.html](./source/index.html) web page and watch the real-time updates.

### Run

#### Main

The main process starts from [download_and_process.py](./source/download_and_process.py). You can use options to control its behavior. Run `python3 download_and_process.py -h` for help.

By default it should start to work as expected. It means it downloads live data and store it into database.

#### Build Models

This function reads all data from database and build models who are saved into specific folder.

You can run it directly from [build_models.py](./source/build_models.py) or use the option and run [download_and_process.py](./source/download_and_process.py).

#### Server

Just run [server.py](./source/server.py). You may need to change port number.

#### App

Deploy [index.html](./source/index.html).
