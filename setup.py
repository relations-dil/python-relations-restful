#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name="relations-restful",
    version="0.1.0",
    package_dir = {'': 'lib'},
    py_modules = [
        'relations.restful',
        'relations.restful.resource',
        'relations.restful.source',
        'relations.restful.unittest'
    ],
    install_requires=[
        'flask==1.1.2',
        'flask_restful==0.3.8'
    ]
)
