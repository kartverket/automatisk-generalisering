import ast
import os
import sys
from pathlib import Path
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
            if node.module:
                imports.add(node.module)
                for alias in node.names:
                    imports.add(f"{node.module}.{alias.name}")
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
    local_modules = set()
    root_dir_str = str(root_dir)
    for lib in imports:
        lib_name = lib.split(".")[0]
        try:
            __import__(lib_name)
            lib_file = sys.modules[lib_name].__file__
            if lib_file and not lib_file.startswith(root_dir_str):
                external_libs.add(lib)
            else:
                local_modules.add(lib)
        except ImportError:
            external_libs.add(lib)
        except AttributeError:
            if lib.startswith(root_dir_str):
                local_modules.add(lib)
            else:
                external_libs.add(lib)
    return external_libs, local_modules


def create_dependency_graph(
    dependencies, external_libs, output_file="dependency_graph.html"
):
    net = Network(height="1500px", width="100%", bgcolor="#222222", font_color="white")
    net.barnes_hut()

    for file in dependencies.keys():
        net.add_node(file, label=file)
        print(f"Added node: {file}")

    for file, deps in dependencies.items():
        for dep in deps:
            if dep and dep not in external_libs:
                dep_file = find_file_path(dep, dependencies.keys())
                if dep_file:
                    net.add_edge(file, dep_file)
                    print(f"Added edge from {file} to {dep_file}")
                else:
                    print(
                        f"Dependency {dep} not found for {file} - Attempting alternate path resolution."
                    )
                    alt_dep_file = find_alternate_file_path(dep, dependencies.keys())
                    if alt_dep_file:
                        net.add_edge(file, alt_dep_file)
                        print(
                            f"Added edge from {file} to {alt_dep_file} (via alternate path resolution)"
                        )
                    else:
                        print(
                            f"Dependency {dep} not found for {file} (after alternate path resolution)"
                        )

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
            print(f"Found file for module {module_name}: {possible_files[0]}")
            return possible_files[0]
    print(f"No file found for module {module_name}")
    return None


def find_alternate_file_path(module_name, files):
    module_parts = module_name.split(".")
    if len(module_parts) > 1:
        module_path = "/".join(module_parts[:-1])
        module_name = module_parts[-1]
        possible_files = [
            f
            for f in files
            if f.startswith(module_path) and f.endswith(f"/{module_name}.py")
        ]
        if possible_files:
            print(
                f"Found file for module {module_name} (alternate resolution): {possible_files[0]}"
            )
            return possible_files[0]
    print(f"No alternate file found for module {module_name}")
    return None


if __name__ == "__main__":
    root_dir = Path(__file__).parent
    dependencies, all_imports = analyze_project(root_dir)
    external_libs, local_modules = identify_external_libraries(root_dir, all_imports)
    print(f"External libraries: \n{external_libs}")
    print(f"\nLocal modules: \n{local_modules}")
    create_dependency_graph(dependencies, external_libs)
