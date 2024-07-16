import ast
import os
import sys
from pyvis.network import Network


def find_imports(filepath):
    with open(filepath, "r") as file:
        tree = ast.parse(file.read(), filename=filepath)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module)
    return imports


def analyze_project(root_dir):
    dependencies = {}
    all_imports = set()
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                full_path = os.path.relpath(os.path.join(subdir, file), root_dir)
                file_imports = find_imports(os.path.join(subdir, file))
                dependencies[full_path] = file_imports
                all_imports.update(file_imports)
                print(f"{full_path}: {file_imports}")
    return dependencies, all_imports


def identify_external_libraries(root_dir, imports):
    external_libs = set()
    for lib in imports:
        try:
            # Check if the library can be imported
            __import__(lib)
            # Find the library's file location
            lib_file = sys.modules[lib].__file__
            # Check if the file is outside the project root
            if lib_file and not lib_file.startswith(root_dir):
                external_libs.add(lib)
        except ImportError:
            # If the import fails, it's an external library
            external_libs.add(lib)
        except AttributeError:
            # Some built-in modules don't have __file__ attribute
            pass
    return external_libs


def create_dependency_graph(
    dependencies, external_libs, output_file="dependency_graph.html"
):
    net = Network(height="1500px", width="100%", bgcolor="#222222", font_color="white")

    net.barnes_hut()

    # Add all nodes first
    for file in dependencies.keys():
        net.add_node(file, label=file)
        print(f"Added node: {file}")

    # Add edges for dependencies that exist as nodes and are not external libraries
    for file, deps in dependencies.items():
        for dep in deps:
            if dep and dep not in external_libs:
                dep_file = find_file_path(dep, dependencies.keys())
                if dep_file:
                    net.add_edge(file, dep_file)
                    print(f"Added edge from {file} to {dep_file}")
                else:
                    print(f"Dependency {dep} not found for {file}")

    # Use save_graph to generate the HTML file
    net.save_graph(output_file)
    print(f"Graph saved to {output_file}")


def find_file_path(module_name, files):
    module_parts = module_name.split(".")
    for i in range(len(module_parts), 0, -1):
        module_path = "/".join(module_parts[:i])
        possible_files = [
            f
            for f in files
            if f.startswith(module_path)
            and (f.endswith(".py") or f.endswith("/__init__.py"))
        ]
        if possible_files:
            return possible_files[0]
    return None


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dependencies, all_imports = analyze_project(root_dir)
    external_libs = identify_external_libraries(root_dir, all_imports)
    print(f"External libraries: {external_libs}")
    create_dependency_graph(dependencies, external_libs)
