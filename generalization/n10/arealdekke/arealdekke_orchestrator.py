from generalization.n10.arealdekke.arealdekke_dissolver import (
    partition_call as arealdekke_dissolver,
)
from generalization.n10.arealdekke.gangsykkel_dissolver import (
    partition_call as gangsykkel_dissolver,
)
from generalization.n10.arealdekke.eliminate_small_polygons import (
    partition_call as eliminate_small_polygons,
)
from generalization.n10.arealdekke.attribute_changer import attribute_changer
from generalization.n10.arealdekke.island_controller import island_controller
from generalization.n10.arealdekke.passability_layer import create_passability_layer
from generalization.n10.arealdekke.expansion_controller import expand_land_use

from input_data import input_n10
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    MAP_SCALE = "N10"

    environment_setup.main()

    attribute_changer(
        input_fc=input_n10.Arealdekke_Oslo,
        output_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
    )

    create_passability_layer(
        input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
        output_fc=Arealdekke_N10.passability__n10_land_use.value,
    )

    arealdekke_dissolver(
        input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
        output_fc=Arealdekke_N10.dissolve_arealdekke.value,
        map_scale=MAP_SCALE,
    )

    island_controller(
        input_fc=Arealdekke_N10.dissolve_arealdekke.value,
        output_fc=Arealdekke_N10.island_merger_output__n10_land_use.value,
    )

    eliminate_small_polygons(
        input_fc=Arealdekke_N10.island_merger_output__n10_land_use.value,
        output_fc=Arealdekke_N10.elim_output.value,
        map_scale=MAP_SCALE,
    )

    gangsykkel_dissolver(
        input_fc=Arealdekke_N10.elim_output.value,
        output_fc=Arealdekke_N10.dissolve_gangsykkel.value,
        map_scale=MAP_SCALE,
    )

    expand_land_use(
        input_fc=Arealdekke_N10.dissolve_gangsykkel.value,
        output_fc=Arealdekke_N10.expansion_controller_output__n10_land_use.value,
    )


if __name__ == "__main__":
    main()
