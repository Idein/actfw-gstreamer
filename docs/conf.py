# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import sphinx.ext.apidoc
import sphinx_theme
sys.path.insert(0, os.path.abspath('../'))


def setup(app):
    sphinx.ext.apidoc.main(['-f', '-o', 'docs', '.'])

# -- Project information -----------------------------------------------------


project = 'actfw-gstreamer'
copyright = '2021, Idein Inc.'
author = 'Idein Inc.'

# The full version, including alpha/beta/rc tags
exec(open(os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'actfw_gstreamer', '_version.py')).read())
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
# extensions = ['sphinx.ext.autodoc']
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'neo_rtd_theme'
html_theme_path = [sphinx_theme.get_html_theme_path(html_theme)]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []


autoclass_content = 'both'