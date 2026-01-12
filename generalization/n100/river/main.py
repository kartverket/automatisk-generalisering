# Importing modules
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


# Importing building scripts
from generalization.n100.river import data_preparation


@timing_decorator
def main():
    environment_setup.main()
    data_preparation.main()


if __name__ == "__main__":
    main()
