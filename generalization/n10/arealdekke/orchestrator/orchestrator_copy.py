from pathlib import Path

from arealdekke_class import Arealdekke
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from input_data import input_n10#, input_test_data


@timing_decorator
def main():
    environment_setup.main()

    # Creates an instance of the arealdekke object.
    #input_data = input_test_data.arealdekke_1
    input_data=r"H:\SKTemp\hjejak\Automatisk_Generalisering.gdb\Arealdekke_Begrenset_1"
    arealdekke = Arealdekke(input_data=input_data, map_scale="N10")

    arealdekke.preprocess()

    # Adds the categories to the arealdekke object
    yml_file = Path(__file__).parent / "arealdekke_categories_config.yml"
    arealdekke.add_categories(yml_file)

    # Process categories
    arealdekke.process_categories()

    # Final post-processing of the results
    arealdekke.finish_results()


if __name__ == "__main__":
    main()
