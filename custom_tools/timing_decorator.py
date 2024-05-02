import time
import inspect
import os
from functools import wraps

from file_manager.n100.file_manager_buildings import Building_N100


TIMING_DECORATOR_LOG_FILE_USED = False


def timing_decorator(func):
    """Logs the execution time of a function to both the console and a log file"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        result = func(*args, **kwargs)

        elapsed_time = compute_elapsed_time(start_time)

        function_name = func.__name__
        file_path = inspect.getfile(func)
        file_name = os.path.basename(file_path)

        formatted_file_name = file_name.ljust(40)
        formatted_function_name = function_name.ljust(55)

        log_to_console_and_file(
            f"File name: {formatted_file_name} Function name: {formatted_function_name}",
            elapsed_time,
        )

        return result

    return wrapper


def compute_elapsed_time(start_time):
    """Computes the elapsed time given a starting time"""
    elapsed_time_seconds = time.time() - start_time

    elapsed_minutes, elapsed_seconds = divmod(elapsed_time_seconds, 30)

    return elapsed_minutes, elapsed_seconds


def log_to_console_and_file(function_name, elapsed_time):
    """Logs a messages to both the console and a file"""
    elapsed_minutes, elapsed_seconds = elapsed_time
    output = f"{function_name} Execution time: {int(elapsed_minutes)} minutes {elapsed_seconds:.0f} seconds".ljust(
        60
    )

    log_to_console(output)
    log_to_file(output)


def log_to_console(message):
    """Prints a given message to the console"""
    print(message)


def log_to_file(message):
    """Writes a given message to a log file"""

    global TIMING_DECORATOR_LOG_FILE_USED

    log_file_path = Building_N100.overview__runtime_all_building_functions__n100.value

    if os.path.exists(log_file_path) and not TIMING_DECORATOR_LOG_FILE_USED:
        # if it's the first time this runtime, delete the log file
        os.remove(log_file_path)

    TIMING_DECORATOR_LOG_FILE_USED = True

    with open(log_file_path, "a") as f:
        f.write(message + "\n")
