from pathlib import Path

from arealdekke_class import Arealdekke

from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup

from input_data import input_area
from input_data.input_orchestrator import InputDataOrchestrator


@timing_decorator
def main():
    environment_setup.main()

    # Creates an instance of the arealdekke object.
    map_scale = "N10"
    data_orc = InputDataOrchestrator(map_scale=map_scale)
    data_orc.set_input_dataset(input_area)
    area_data = data_orc.get_dataset("AREA")
    input_data = area_data.Arealdekke_Begrenset_1

    # If True = only final output will be available after generalization
    # If False = all intermediate files not deleted by wfm will be available (default)
    only_keep_final_output = False

    arealdekke = Arealdekke(
        input_data=input_data,
        data_orc=data_orc,
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
