# Makes sure the path is relative to the root path
import sys
root_path = detect()
sys.path.append(root_path)

# Importing config file from the root path
import config

# Defining universal paths for other files regardless of local path setup
matrikkel_bygningspunkt = fr"{config.matrikkel_path}\bygning"