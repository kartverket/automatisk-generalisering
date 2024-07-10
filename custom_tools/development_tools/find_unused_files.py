import os
import ast
from file_manager.n100.file_manager_buildings import Building_N100


def get_enum_members(enum_class):
    return {name for name, member in enum_class.__members__.items()}


def find_python_files(root_dir):
    python_files = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(subdir, file))
    return python_files


def get_used_enum_members_in_file(file_path, enum_class):
    used_members = set()
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            source = file.read()
    except UnicodeDecodeError:
        print(f"Skipping file due to encoding error: {file_path}")
        return used_members

    tree = ast.parse(source)

    class_name = enum_class.__name__

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == enum_class.__module__:
            for alias in node.names:
                if alias.name == class_name:
                    imported_as = alias.asname if alias.asname else alias.name
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Attribute) and isinstance(
                            node.value, ast.Name
                        ):
                            if node.value.id == imported_as:
                                used_members.add(node.attr)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == enum_class.__module__:
                    imported_as = alias.asname if alias.asname else alias.name
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Attribute) and isinstance(
                            node.value, ast.Attribute
                        ):
                            if (
                                node.value.value.id == imported_as
                                and node.value.attr == class_name
                            ):
                                used_members.add(node.attr)

    return used_members


def get_used_enum_members_in_project(root_dir, enum_class):
    used_members = set()
    python_files = find_python_files(root_dir)
    for file_path in python_files:
        used_members.update(get_used_enum_members_in_file(file_path, enum_class))
    return used_members


if __name__ == "__main__":
    # Get the directory of the current script file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Set the project root directory relative to the current script directory
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))

    all_members = get_enum_members(Building_N100)
    used_members = get_used_enum_members_in_project(project_root, Building_N100)
    unused_members = all_members - used_members

    print(f"Unused members of {Building_N100.__name__}:")
    for member in unused_members:
        print(member)
