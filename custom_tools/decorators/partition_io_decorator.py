def partition_io_decorator(input_param_names=None, output_param_names=None):
    def decorator(func):
        setattr(
            func,
            "_partition_io_metadata",
            {"inputs": input_param_names, "outputs": output_param_names},
        )
        return func

    return decorator
