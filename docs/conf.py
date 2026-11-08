# Configuration file for the Sphinx documentation builder.

project = "PropulPy"
copyright = "2026, Anderson Chica Restrepo"
author = "Anderson Chica Restrepo"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
]

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "amsmath",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_theme_options = {
    "github_url": "https://github.com/UltraLuminics/PropulPy",
    "show_nav_level": 2,
    "navigation_depth": 3,
}
