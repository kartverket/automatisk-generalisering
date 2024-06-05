class BufferIncrementCalculator:
    def __init__(
        self,
        largest_road_dimension,
        buffer_displacement_meter,
        maximum_buffer_increase_tolerance,
    ):
        self.largest_road_dimension = largest_road_dimension
        self.buffer_displacement_meter = buffer_displacement_meter
        self.maximum_buffer_increase_tolerance = maximum_buffer_increase_tolerance
        self.tolerance = maximum_buffer_increase_tolerance - 0.5
        self.target_value = largest_road_dimension + buffer_displacement_meter
        self.previous_value = 0
        self.current_value = 0
        self.rest_value = 0
        self.iteration_fixed_buffer_addition = 0
        self.increments = []

    def calculate_buffer_increments(self):
        iteration_buffer_factor = 0

        found_valid_increment = False

        while iteration_buffer_factor < 1:
            next_buffer_factor = iteration_buffer_factor + 0.001

            if not found_valid_increment:
                increment_value = next_buffer_factor * self.largest_road_dimension
            else:
                increment_value = (
                    next_buffer_factor * self.largest_road_dimension
                ) - self.previous_value

            if increment_value >= self.tolerance:
                if not found_valid_increment:
                    iteration_buffer_factor = next_buffer_factor - 0.001
                self.increments.append((iteration_buffer_factor, 0))
                self.current_value = (
                    iteration_buffer_factor * self.largest_road_dimension
                )
                self.previous_value = self.current_value
                found_valid_increment = True
                iteration_buffer_factor = next_buffer_factor

                continue

            iteration_buffer_factor = next_buffer_factor
            self.current_value = iteration_buffer_factor * self.largest_road_dimension

        if self.previous_value != self.current_value:
            self.current_value = self.largest_road_dimension
            increase_from_last_cleanup = self.current_value - self.previous_value

            self.rest_value = self.tolerance - increase_from_last_cleanup

            self.increments.append((1, self.rest_value))
            self.current_value = self.rest_value
        else:
            self.current_value = 0

        self.target_value = self.buffer_displacement_meter

        while self.current_value <= self.target_value:
            missing_value = self.target_value - self.current_value

            if missing_value <= self.tolerance:
                self.increments.append((1, self.buffer_displacement_meter))

                break

            increment_value = min(self.tolerance, missing_value)
            self.iteration_fixed_buffer_addition = increment_value + self.current_value

            self.increments.append((1, self.iteration_fixed_buffer_addition))
            self.current_value = self.iteration_fixed_buffer_addition

        return self.increments


# Example usage
calculator = BufferIncrementCalculator(
    largest_road_dimension=133,
    buffer_displacement_meter=201,
    maximum_buffer_increase_tolerance=22.5,
)
increments = calculator.calculate_buffer_increments()

print(increments)
