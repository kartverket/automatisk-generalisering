# Arealdekke unittests

The areakdekke test folder includes several tests for the Category, Program History and Arealdekke classes. All of these tests use the python unittest library (pytest) and its mocking modules to ensure that each automated test does not affect each other. 

Note that some of them may be outdated, as they were used during early development. 

## How to Use
Unittests have to run from the root of the project. This can be tricky, as the buildt-in VSCode terminal does not run the same python version as the rest of the project by default. 

The most straight forward way of fixing this is to edit the settings in VSCode to make the terminal use the same python version as the project. Afterwards, you will be able to run the script form the terminal with no problems.

Another solution is to paste ``& "{file_path_to_your_arcgispro_python_interpeter}" -m pytest`` in the terminal each time you want to run the tests. This line commands VSCode to use the python interpeter bundled with ArcGIS Pro and execute the pytest module as main.

## General structure of pytest

All test class- and function names must begin "test_" for pytest to run them. This excludes the functions included in pytest to automate the unittests:

**setUpClass(cls)** - Runs before *all* tests. E.g. establishing database connections, etc.

**setUp(self)** - Runs before *each* test. E.g. mocks that can be used by each test.

**tearDown(self)** - Runs after *each* test. E.g. delete mocks after a test is done.

**tearDownClass(cls)** - Runs after *all* tests. E.g. shut down database connections.