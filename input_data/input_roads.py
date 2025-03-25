import config
from config import roads_path, road_output
import arcpy
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n100.file_manager_buildings import Building_N100

vegsenterlinje = rf"{roads_path}\vegsenterlinje"
elveg = rf"{roads_path}\elveg"
annet_elveg = rf"{roads_path}\annet_elveg"
elveg_and_sti = rf"{roads_path}\elveg_and_sti"
elveg_and_sti_oslo = rf"{roads_path}\elveg_and_sti_Oslo"
FunksjonellVegklasse = rf"{roads_path}\FunksjonellVegklasse"
Kjørebane = rf"{roads_path}\Kjørebane"
Kjørefelt = rf"{roads_path}\Kjørefelt"
Motorveg = rf"{roads_path}\Motorveg"
Ramper = rf"{roads_path}\Ramper"
Sti = rf"{roads_path}\Sti"
Veglenke = rf"{roads_path}\Veglenke"
Vegtrase = rf"{roads_path}\Vegtrase"
roads = rf"{roads_path}\roads"

road_output_1 = rf"{road_output}\n100_Veg2025_Norge4"

if __name__ == "__main__":
    environment_setup.main()

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.data_selection___road_n100_input_data___n100_building.value,
        in_symbology_layer=config.symbology_samferdsel,
        output_name=Road_N100.data_selection___new_road_symbology___n100_road_lyrx.value,
        grouped_lyrx=True,
        target_layer_name="N100_Samferdsel_senterlinje_veg_bru_L2",
    )
