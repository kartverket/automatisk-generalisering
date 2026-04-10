from pathlib import Path

from arealdekke_class import Arealdekke
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    environment_setup.main()

    # Creates an instance of the arealdekke object.
    arealdekke = Arealdekke("N10")

    arealdekke.preprocess()

    # Adds the categories to the arealdekke object
    yml_file = Path(__file__).parent / "arealdekke_categories_config.yml"
    arealdekke.add_categories(yml_file)

    # Process categories
    arealdekke.process_categories()


if __name__ == "__main__":
    main()
