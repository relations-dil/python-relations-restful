#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name="python-relations-restful",
    version="0.6.1",
    package_dir = {'': 'lib'},
    py_modules = [
        'relations_restful',
        'relations_restful.resource',
        'relations_restful.source',
        'relations_restful.unittest'
    ],
    install_requires=[
        'requests==2.25.1',
        'flask==2.0.3',
        'flask_restful==0.3.9'
    ]
)
