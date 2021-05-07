"""
Utilities for Relations RESTful
"""

import inspect

import flask_restful

from relations_restful.resource import ResourceError, ResourceIdentity, Resource, exceptions
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

    class Model(flask_restful.Resource):
        """
        Custom class for each call
        """

        MODELS = []

        def get(self):
            """
            List all models
            """
            return {"models": self.MODELS}

    restful.add_resource(Model, "/model")

    for resource in resources(module) + ensure(module, models):

        thy = resource.thy()

        Model.MODELS.append({
            "id": thy.model._id,
            "label": thy.model._label,
            "title": thy.model.TITLE,
            "singular": thy.SINGULAR,
            "plural": thy.PLURAL,
            "list": thy.LIST
        })

        if resource.__name__.lower() not in restful.endpoints:
            restful.add_resource(resource, *thy.endpoints())
