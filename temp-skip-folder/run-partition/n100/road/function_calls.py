from composition_configs import core_config, logic_config
from custom_tools.generalization_tools.road.thin_road_network import ThinRoadNetwork


def thin_road_network(*, input: logic_config.DataRef, output: logic_config.DataRef) -> None:
    cfg = logic_config.ThinRoadNetworkKwargs(
        input_road_line=input.path,
        output_road_line=output.path,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=input.path,
            write_to_memory=False,
            keep_files=False,
        ),
        minimum_length=1400,
        invisibility_field_name="invisibility",
        hierarchy_field_name="hierarchy",
        special_selection_sql=None,
    )

    ThinRoadNetwork(cfg).run()
