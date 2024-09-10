"""
What:
    This module provides examples of how to structure and document Python functions and classes
    using the `what`, `how`, and `why` documentation structure. It includes examples of small
    functions, callable functions, and classes with utility methods.

How:
    The functions in this file demonstrate various patterns for interacting with parameters,
    returning values, and using class-based methods. Each function or method is documented
    to illustrate the approach.

Why:
    This file is intended to serve as a guideline for developers in the project, providing a
    consistent approach to writing and documenting Python code.
"""


def example_of_small_function():
    """
    Does something needing little explanation outside reading the code.
    """
    x = 1 + 1
    print(x)


def example_small_function_taking_args_with_returns(parameter: str) -> str:
    """
    What:
        Does something with parameter, returns parameter_2.
        This logic is easy to understand from the code so the most important
        is what is required from the parameter, and what it returns.

    Args:
        parameter: The string used in something. Important information regarding the parameter is informed about.

    Returns:
        str: A modified string used for something else.
    """
    parameter_2 = f"Does something with {parameter}"

    return parameter_2


def example_of_large_function():
    """
    What:
        Calls example_of_small_function and example_small_function_taking_args_with_returns, then prints a modified version of their results.
        This function does not take any arguments or return anything, but it requires an explanation due to its complexity.

    How:
        Using math in the example_of_small_function we get the value of x.
        Then we use f on parameter to return parameter_2 which we use to create something_completely_different.
        We then print something_completely_different.

    Why:
        It is important to know what something_completely_different is so that we can think about it.
    """

    example_of_small_function()
    parameter_2 = example_small_function_taking_args_with_returns(parameter="something")

    something_completely_different = f"something { parameter_2}"
    print(something_completely_different)


def example_of_callable_function(
    parameter: str,
    parameter_2: int,
    parameter_3: bool,
) -> str:
    """
    What:
        Iterates over a range defined by parameter_2 and prints or constructs a string
        based on the value of parameter_3. If it is less clear what the parameters are intended to do,
        it is important to put focus on how the function is supposed to be used since it is intended to be called.

    Args:
        parameter: A string that will be included in the printed or constructed message.
        parameter_2: An integer representing the number of iterations.
        parameter_3: A boolean that determines whether to print the message or construct it silently.

    Returns:
        str: The final value constructed in the loop.
    """
    value = ""
    for i in range(parameter_2):
        if parameter_3:
            print(f"The amount of times I have printed {parameter} is now: {i}")
        else:
            value = f"But sometimes it is ok not to print {parameter}, current iteration is: {i}"

    return value


def example_main():
    """
    What:
        The main function orchestrates the workflow of various functions related to data processing,
        including environment setup, data selection, and multiple steps of spatial analysis.

    How:
        It calls a series of predefined functions in a specific order, ensuring the correct data is selected,
        processed, and classified. The functions perform tasks like setting up the environment, selecting urban areas,
        reclassifying values, and merging data points and polygons from different sources.

    Why:
        The `main()` function centralizes the execution logic, ensuring that all necessary steps are
        performed in the correct sequence. This makes the workflow easier to manage, maintain, and understand.
    """
    example_of_small_function()
    example_of_small_function()
    example_of_small_function()


class ExampleClass:
    """
    What:
        This class encapsulates utility functions that interact with the class's parameters.
        It exposes a main callable function (`run`), which combines the logic of the smaller functions.

    How:
        The class provides two utility methods: `example_of_small_function` and
        `example_small_function_taking_args_with_returns`. The `run` method combines these
        functions to process the class-level parameters and is intended to be used externally.

    Why:
        Organizing the logic into smaller utility functions makes it easier to test, reuse, and
        extend. The `run` method centralizes the usage of the utility functions for ease of interaction.

    Example Usage:
        ```python
        example_instance = ExampleClass(parameter="test", parameter_2=5, parameter_3=True)
        result = example_instance.run()
        print(result)
        ```
    """

    def __init__(
        self,
        parameter: str,
        parameter_2: int,
        parameter_3: bool,
    ):
        """
        What:
            Initializes the class with three parameters that will be processed in various utility methods.

        Args:
            parameter: A string that will be processed in various class methods.
            parameter_2: An integer used to control the number of iterations in loops.
            parameter_3: A boolean controlling how parameters are processed or printed.
        """
        self.parameter = parameter
        self.parameter_2 = parameter_2
        self.parameter_3 = parameter_3

    def example_of_small_function(self):
        """
        What:
            A small function that modifies the class attribute `self.parameter_2` and prints the updated value.
        """
        self.parameter_2 += 1
        print(f"The value of parameter_2 has been incremented to: {self.parameter_2}")

    def example_small_function_taking_args_with_returns(
        self, additional_param: str
    ) -> str:
        """
        What:
            This function takes an additional string argument, processes it with `self.parameter`,
            and returns a modified string based on the current state of the class.

        Args:
            additional_param: An additional string that will be combined with `self.parameter`.

        Returns:
            str: A modified string that combines `self.parameter` and `additional_param`.
        """
        result = f"{self.parameter} and {additional_param} combined into something new."
        return result

    def run(self) -> str:
        """
        What:
            This is the main callable function that combines the logic of `example_of_small_function`
            and `example_small_function_taking_args_with_returns`, returning the final processed result.

        How:
            It first increments `self.parameter_2` using `example_of_small_function`, then processes
            `self.parameter` and an additional string using `example_small_function_taking_args_with_returns`.

        Why:
            This method centralizes the logic from the utility functions and provides a single point of
            interaction with the class's functionality.

        Returns:
            str: The final processed message after combining `self.parameter` with the additional string.
        """
        # Call the small utility function to modify and print `self.parameter_2`
        self.example_of_small_function()

        # Call the utility function that takes an argument and returns a processed string
        result = self.example_small_function_taking_args_with_returns(
            "additional information"
        )

        return result
