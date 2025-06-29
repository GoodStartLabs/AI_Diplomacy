# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
"""Package installer"""

import os
import sys
from setuptools import setup, find_packages

# Import the current version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "diplomacy"))
from version import PACKAGE_VERSION

# Requiring python 3.5+.
# To simplify code for Tornado coroutines return statements, we don't support Python 3.4
# ( more info here: http://www.tornadoweb.org/en/stable/guide/coroutines.html#coroutines ).
if (sys.version_info.major, sys.version_info.minor) <= (3, 4):
    print(
        "This package is only compatible with Python 3.5+, but you are running Python {}.{}.".format(
            sys.version_info.major, sys.version_info.minor
        )
    )

# ------------------------------------
# Configuration
setup(
    name="diplomacy",
    version=PACKAGE_VERSION,
    description="Diplomacy: DATC-Compliant Game Engine with Web Interface",
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    long_description_content_type="text/markdown",
    url="https://github.com/diplomacy/diplomacy",
    author="Philip Paquette",
    author_email="pcpaquette@gmail.com",
    packages=find_packages(),
    keywords="diplomacy diplomacy-game game negotiation",
    python_requires=">=3.5",
    include_package_data=True,
    install_requires=[
        "bcrypt",
        "coloredlogs",
        "python-dateutil",
        "pytz",
        "tornado>=5.0",
        "tqdm",
        "ujson",
    ],
    tests_require=["pytest"],
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Games/Entertainment :: Board Games",
    ],
    project_urls={
        "Bug Reports": "https://github.com/diplomacy/diplomacy/issues",
        "Documentation": "https://diplomacy.readthedocs.io/",
        "Source": "https://github.com/diplomacy/diplomacy/",
    },
)

# ------------------------------------
