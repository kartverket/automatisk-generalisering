# Importing modules
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


# Importing road scripts
from generalization.n100.road import data_preparation


# Main function that runs all the road scripts
@timing_decorator
def main():
    data_preparation.main()


if __name__ == "__main__":
    main()
