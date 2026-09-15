"""
Generate a Mermaid class hierarchy document from Python source files.

The module parses Python files with :mod:`ast`, extracts class inheritance and
member information, and writes the resulting Mermaid diagram to
``classHierarchy.md`` in the configured source folder.
"""

import ast
from pathlib import Path

###############################
# Program
###############################


def main() -> None:
    """
    Generate and write the class hierarchy document.

    The source folder is configured in this entry point. The files are then
    inspected and the extracted information is rendered as Mermaid markup.
    """
    path: str = r"..."
    root: Path = Path(path)
    relations, classes = read_files(root)
    markdown = build_mermaid(relations, classes)

    (root / "classHierarchy.md").write_text(markdown, encoding="utf-8")


###############################
# Main functions
###############################


def read_files(
    root: Path,
) -> tuple[list[tuple[str, str]], dict[str, dict[str, list[str]]]]:
    """
    Extract class relationships and members from Python files below ``root``.

    Files whose names start with an underscore are skipped. Only direct bases
    represented by simple names are included in the inheritance relations.

    Args:
        root: Folder to search recursively for Python files.

    Returns:
        A tuple containing inheritance relations and class member information.
    """
    relations: list[tuple[str, str]] = []
    classes: dict[str, dict[str, list[str]]] = {}

    for py_file in root.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            class_name = node.name

            classes[class_name] = {"attributes": [], "methods": []}

            # Inheritance
            _find_inheritance(node, class_name, relations)

            # Class attributes and methods
            _find_class_info(node, class_name, classes)

    return relations, classes


def build_mermaid(
    relations: list[tuple[str, str]],
    classes: dict[str, dict[str, list[str]]],
) -> str:
    """
    Render extracted class information as a Mermaid class diagram.

    Relations, classes, attributes, and methods are sorted to make the
    generated document deterministic. Duplicate members are emitted once.

    Args:
        relations: Parent-child class relationships as ``(parent, child)``.
        classes: Class names mapped to their attributes and method signatures.

    Returns:
        A Markdown document containing a Mermaid ``classDiagram`` block.
    """
    md = ["# Class Hierarchy", "", "```mermaid", "classDiagram"]

    # Inheritance
    for parent, child in sorted(relations):
        md.append(f"    {parent} <|-- {child}")

    md.append("")

    # Class diagram
    for class_name, info in sorted(classes.items()):
        md.append(f"    class {class_name} {{")

        for attribute in sorted(set(info["attributes"])):
            md.append(f"        {attribute}")

        for method in sorted(set(info["methods"])):
            md.append(f"        {method}")

        md.append("    }")
        md.append("")

    md.append("```")

    return "\n".join(md)


###############################
# Helper functions
###############################


def _find_inheritance(
    node: ast.ClassDef, class_name: str, relations: list[tuple[str, str]]
) -> None:
    """Append the class's direct, simple-name bases to ``relations``."""
    for base in node.bases:
        if isinstance(base, ast.Name):
            relations.append((base.id, class_name))


def _find_class_info(
    node: ast.ClassDef, class_name: str, classes: dict[str, dict[str, list[str]]]
) -> None:
    """
    Collect class attributes, method signatures, and ``self`` assignments.

    Class-level assignments and annotated assignments become attributes. Each
    method is represented by its name, parameters, and optional return type;
    assignments to ``self`` inside ``__init__`` are also included as instance
    attributes.
    """
    for member in node.body:
        # Class attributes
        if isinstance(member, ast.Assign):
            for target in member.targets:
                if isinstance(target, ast.Name):
                    classes[class_name]["attributes"].append(f"+{target.id}")
        # Typehint attributes
        elif isinstance(member, ast.AnnAssign):
            if isinstance(member.target, ast.Name):
                name = member.target.id

                if member.annotation:
                    type_name = ast.unparse(member.annotation)
                else:
                    type_name = "Any"

                classes[class_name]["attributes"].append(f"+{type_name} {name}")
        # Methods
        elif isinstance(member, ast.FunctionDef):
            args = []

            for arg in member.args.args:
                if arg.arg == "self":
                    continue

                if arg.annotation:
                    arg_type = ast.unparse(arg.annotation)
                    args.append(f"{arg.arg}: {arg_type}")
                else:
                    args.append(arg.arg)

            return_type = ""

            if member.returns:
                return_type = ast.unparse(member.returns)

            signature = f"+{member.name}({', '.join(args)})"
            if return_type:
                signature += f" {return_type}"

            classes[class_name]["methods"].append(signature)

            if member.name == "__init__":
                for stmt in ast.walk(member):
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Attribute)
                        and isinstance(stmt.targets[0].value, ast.Name)
                        and stmt.targets[0].value.id == "self"
                    ):
                        classes[class_name]["attributes"].append(
                            f"+{stmt.targets[0].attr}"
                        )


###############################


if __name__ == "__main__":
    main()
