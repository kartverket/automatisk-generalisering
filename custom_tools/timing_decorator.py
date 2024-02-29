import time
from functools import wraps

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100

import time
from functools import wraps

# Importing temporary files
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


# Total elapsed time accumulator
total_elapsed_time = 0

# Calculate total elapsed time
for line in print_output:
    minutes = int(line.split(":")[1].split()[0])
    seconds = float(line.split(":")[1].split()[2])
    total_elapsed_time += minutes * 60 + seconds

# Write all print statements to a file
output_file = Building_N100.overview__runtime_all_building_functions__n100.value

# Write total elapsed time to the file
with open(output_file, "w") as f:
    f.write(
        f"Total run time: {int(total_elapsed_time // 3600)} hours {int((total_elapsed_time % 3600) // 60)} minutes {total_elapsed_time % 60:.2f} seconds\n\n"
    )

    # Write all print statements to the file with additional newline characters
    for line in print_output:
        f.write(line + "\n")
