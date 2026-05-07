from pathlib import Path

from arealdekke_class import Arealdekke
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator

from input_data import input_n10


@timing_decorator
def main():
    environment_setup.main()

    # Creates an instance of the arealdekke object.
    input_data = input_n10.arealdekkeflate
    map_scale = "N10"

    # If True = only final output will be available after generalization
    # If False = all intermediate files not deleted by wfm will be available (default)
    only_keep_final_output = False

    arealdekke = Arealdekke(
        input_data=input_data,
        map_scale=map_scale,
        only_keep_final_output=only_keep_final_output,
    )

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
