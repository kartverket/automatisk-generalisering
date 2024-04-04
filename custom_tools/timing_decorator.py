import time
from functools import wraps

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# List to store print statements
print_output = []


# Decorator to measure execution time of functions
def timing_decorator(arg=None):
    if isinstance(arg, str):  # If arg is a string, use it as a custom name
        custom_name = arg

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                elapsed_time = end_time - start_time
                minutes = int(elapsed_time // 60)
                seconds = elapsed_time % 60
                output = f"{custom_name} execution time: {minutes} minutes {seconds:.2f} seconds"
                print_output.append(output)  # Append to the list
                return result

            return wrapper

        return decorator
    else:  # If arg is not a string (or None), use the function name as the default name
        func = arg

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            output = f"{func.__name__} execution time: {minutes} minutes {seconds:.2f} seconds"
            print_output.append(output)  # Append to the list
            return result

        return wrapper


def write_to_file():
    output_file = Building_N100.overview__runtime_all_building_functions__n100.value
    with open(output_file, "w") as f:
        for output in print_output:
            f.write(output + "\n")


def clear_print_output():
    global print_output
    print_output = []
