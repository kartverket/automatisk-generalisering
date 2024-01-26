import time


class Timer:
    def __init__(self):
        self.timings = []
        self.function_counter = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
            int(hours), int(minutes), seconds
        )
        self.timings.append((self.function_counter, time_str))
        self.function_counter += 1

    def print_overview(self):
        print("Function Timings:")
        for i, (function_number, timing) in enumerate(self.timings, start=1):
            print(f"Function {function_number}: {timing}")
