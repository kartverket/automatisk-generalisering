import logging
import os

import env_setup.global_config
import config

# Local root directory
local_root_directory = config.output_folder

# Project root directory
project_root_directory = env_setup.global_config.main_directory_name

# General files directory name
general_files_directory_name = env_setup.global_config.general_files_name

# Logging file name
logging_file_name = "app.log"


class LogPath:
    # Predefined class attributes for each scale-object combination
    # These should be replaced with actual paths constructed from your project's structure
    N100Building = rf"{local_root_directory}\{project_root_directory}\{env_setup.global_config.scale_n100}\{env_setup.global_config.object_bygning}\{general_files_directory_name}\{logging_file_name}"
    N100River = rf"{local_root_directory}\{project_root_directory}\{env_setup.global_config.scale_n100}\{env_setup.global_config.object_elv_bekk}\{general_files_directory_name}\{logging_file_name}"


def setup_logger(scale, object_type, log_directory="logs", filename=logging_file_name):
    """
    Creates a logger for the specified scale and object type.
    Log files will be stored in a directory structure matching the scale and object type.

    :param scale: The scale for the log (e.g., 'n100').
    :param object_type: The object type for the log (e.g., 'bygning').
    :param log_directory: Base directory for logs. Defaults to 'logs'.
    :param filename: Default filename for the log. Defaults to 'app.log'.
    :return: Logger instance for the specified scale and object type.
    """
    # Construct the log file path
    log_path = os.path.join(
        config.output_folder,
        env_setup.global_config.main_directory_name,
        scale,
        object_type,
        log_directory,
    )
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    full_log_path = os.path.join(log_path, filename)

    # Configure logger
    logger = logging.getLogger(f"{scale}_{object_type}")
    if not logger.handlers:  # Avoid adding handlers multiple times
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(full_log_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
