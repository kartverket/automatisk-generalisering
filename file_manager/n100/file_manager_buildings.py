from generalization.n100.building import building_data_preparation
from env_setup import environment_setup




# class file_manager:
#     """
#     file_manager is a class designed to manage file locations within the project.
#     It should be used in conjunction with the file_dictionary class to ensure consistency
#     and easy access to file paths.
#
#     Adding a File:
#     --------------
#
#     To add a file, you should do the following:
#
#     1. Import both file_manager and file_dictionary.
#        from file_manager.n100.file_manager_buildings import file_manager, file_dictionary
#
#     2. Define your file variable and add it to the file_manager.
#        file_variable = "file_path"
#        file_manager.add_file("file_path", file_variable)
#
#        Example:
#        output_name_unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"
#        file_manager.add_file("output_name_unsplit_veg_sti_n100", output_name_unsplit_veg_sti_n100)
#
#     Retrieving a File:
#     ------------------
#     To retrieve a file, you can simply call the get_file method from the file_manager, using the keys defined in file_dictionary:
#
#     file_manager.get_file(file_dictionary.file_variable)
#
#     Example:
#     file_manager.get_file(file_dictionary.output_name_unsplit_veg_sti_n100)
#     """
#     _instance = None
#
#     @staticmethod
#     def get_instance():
#         if file_manager._instance is None:
#             file_manager()
#         return file_manager._instance
#
#     def __init__(self):
#         if file_manager._instance is not None:
#             raise Exception("This class is a Singleton!")
#         else:
#             file_manager._instance = self
#             self.file_locations = {}
#
#     def add_file(self, key, location):
#         self.file_locations[key] = location
#
#     def get_file(self, key):
#         return self.file_locations.get(key, "File not found.")
#
#
# class file_dictionary:
#     """
#     This class holds constant keys for file names used in the file manager and is used together with file_manager.
#     Each attribute corresponds to a unique key that is used to store
#     and retrieve file paths in the file_manager class.
#     When you add a file to file_manager the file_dictionary needs to be updated accordingly.
#
#     Example usage:
#         from file_manager.n100.file_manager_buildings import file_manager, file_dictionary
#
#         file_location = file_manager.get_file(file_dictionary.file_name)
#     """
#
#     output_name_unsplit_veg_sti_n100 = (
#         "unsplit_veg_sti_n100"  # Comment about where the file is from and how it's used
#     )
#     selection_fc = "selection_fc"


# file_manager_buildings.py

# class file_manager:
#     file_locations = {}
#
#     @classmethod
#     def add_file(cls, key, location):
#         cls.file_locations[key] = location
#
#     @classmethod
#     def get_file(cls, key):
#         return cls.file_locations.get(key, "File not found.")
#
# selection_fc = building_data_preparation.selection_fc
#
# class file_keys:
#     selection_fc = "selection_fc"
#     output_name_unsplit_veg_sti_n100 = "output_name_unsplit_veg_sti_n100"
#     # ... add more keys as attributes
