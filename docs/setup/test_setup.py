from env_setup import environment_setup
from input_data import input_n50, input_n100

# Importing environment
environment_setup.main()

input_n50.check_paths()
input_n100.check_paths()
