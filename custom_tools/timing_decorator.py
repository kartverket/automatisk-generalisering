import time
from functools import wraps

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
                print(
                    f"{custom_name} execution time: {minutes} minutes {seconds:.2f} seconds"
                )
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
            print(
                f"{func.__name__} execution time: {minutes} minutes {seconds:.2f} seconds"
            )
            return result

        return wrapper
