from typing import Callable, List, Optional


def partition_io_decorator(
    input_param_names: Optional[List[str]] = None,
    output_param_names: Optional[List[str]] = None,
) -> Callable:
    """
    What:
        A decorator that adds metadata about input and output parameters for partitioning logic functions.

    Args:
        input_param_names (Optional[List[str]]): A list of input parameter names for the decorated function.
        output_param_names (Optional[List[str]]): A list of output parameter names for the decorated function.

    Returns:
        Callable: The decorated function with added metadata attributes for inputs and outputs.
    """

    def decorator(func):
        setattr(
            func,
            "_partition_io_metadata",
            {"inputs": input_param_names, "outputs": output_param_names},
        )
        return func

    return decorator
