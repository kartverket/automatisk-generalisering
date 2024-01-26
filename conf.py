import os
import sys
import sphinx_rtd_theme

autodoc_mock_imports = ["arcpy"]

sys.path.insert(0, os.path.abspath("."))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Automatisk Generalisering"
copyright = "2024, Kartverket"
author = "Kartverket"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Add autodoc extension
    "sphinx.ext.napoleon",  # Uncomment this if you use Google/NumPy style docstrings
    "sphinx.ext.viewcode",  # Uncomment this to add links to your source code
    "sphinx.ext.githubpages",  # Add GitHub Pages extension
    "sphinx_rtd_theme",
]

# Preserve the order of members as they appear in the source code
autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]
