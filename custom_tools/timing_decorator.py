import time
import os
from functools import wraps

from file_manager.n100.file_manager_buildings import Building_N100


def timing_decorator(func):
    """Logs the execution time of a function to both the console and a log file"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        result = func(*args, **kwargs)

        elapsed_time = compute_elapsed_time(start_time)

        log_to_console_and_file(func.__name__, elapsed_time)

        return result

    return wrapper


def compute_elapsed_time(start_time):
    """Computes the elapsed time given a starting time"""
    elapsed_time_seconds = time.time() - start_time

    elapsed_minutes, elapsed_seconds = divmod(elapsed_time_seconds, 60)

    return elapsed_minutes, elapsed_seconds


def log_to_console_and_file(function_name, elapsed_time):
    """Logs a messages to both the console and a file"""
    elapsed_minutes, elapsed_seconds = elapsed_time
    output = f"{function_name} execution time: {int(elapsed_minutes)} minutes {elapsed_seconds:.0f} seconds"

    log_to_console(output)
    log_to_file(output)


def log_to_console(message):
    """Prints a given message to the console"""
    print(message)


def log_to_file(message):
    """Writes a given message to a log file"""
    log_file_path = Building_N100.overview__runtime_all_building_functions__n100.value
    with open(log_file_path, "a") as f:
        f.write(message + "\n")
