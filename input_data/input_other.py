# Importing config file from the root path
import config

# Defining universal paths for other files regardless of local path env_setup
matrikkel_bygningspunkt = rf"{config.matrikkel_path}\bygning"
RiverBasins = rf"{config.river_basin_polygon}\Nedborfelt_Vassdragsomr"
