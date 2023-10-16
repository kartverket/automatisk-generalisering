import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)

input_n50.check_paths()
input_n100.check_paths()