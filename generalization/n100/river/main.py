# Importing modules
from custom_tools import general_tools
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


# Importing building scripts
from generalization.n100.river import data_preparation
from generalization.n100.river import fix_river_topology_gaps


@timing_decorator
def main():
    environment_setup.main()
    data_preparation.main()
    fix_river_topology_gaps.main()


if __name__ == "__main__":
    main()
