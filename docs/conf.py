import os
import sys
import datetime

sys.path.insert(0, os.path.abspath("../src"))

project = "FirstTry"
author = "arnab19111987-ops"
year = datetime.datetime.now().year
copyright = f"{year}, {author}"
release = "0.1.9"

extensions = []
templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "alabaster"
html_static_path = ["_static"]
