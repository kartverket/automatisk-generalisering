# ========================
# DatasetNamespace
# ========================


class DatasetNamespace:
    """
    Lightweight container class that exposes dataset feature classes as attributes.

    The class dynamically assigns each key/value pair from the input dictionary
    as an attribute on the instance. Keys become attribute names, and values
    (f.ex. Path objects or strings) become attribute values.

    Attributes:
        <dynamic>: Each key in the provided dictionary becomes an attribute
                   on the instance, pointing to the corresponding dataset path.
    """

    def __init__(self, data: dict):
        """
        Initialize the namespace with the provided dataset dictionary.

        Args:
            data (dict): A dictionary where keys are feature class names and
                values are paths (Path or str) to the corresponding feature classes.
        """
        for key, value in data.items():
            setattr(self, key, value)

    def __repr__(self):
        """
        Return a readable representation listing available feature classes.

        Returns:
            str: A formatted string showing the dataset's attribute names.
        """
        return f"<Dataset {', '.join(self.__dict__.keys())}>"
