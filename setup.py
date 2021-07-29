#!/usr/bin/env python

"""The setup script."""
from setuptools import setup

setup(
    use_scm_version={"write_to": "src/plotski/_version.py"},
    setup_requires=["setuptools_scm"],
)
