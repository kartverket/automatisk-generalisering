import os
import sys

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
]


templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
