"""
Utilities for Relations RESTful
"""

import inspect

from relations_restful.resource import ResourceIdentity, Resource, exceptions
from relations_restful.source import Source

def resources(module):
    """
    List all the resources in a module
    """

    return [
        m[1]
        for m in inspect.getmembers(
            module,
            lambda model: inspect.isclass(model)
            and issubclass(model, Resource)
        )
    ]

def ensure(module, models):
    """
    Creates the Resources for all models
    """

    exists = [resource.MODEL for resource in resources(module)]

    return [
        type(model.__name__, (Resource, ), {'MODEL': model})
        for model in models if model not in exists
    ]

def attach(restful, module, models):
    """
    Attach all Reources to a Restful
    """

    for resource in resources(module) + ensure(module, models):
        if resource.__name__.lower() not in restful.endpoints:
            restful.add_resource(resource, *resource.thy().endpoints())
