"""
Resource module for Relations and Flask RESTful
"""

# pylint: disable=not-callable

import flask
import flask_restful

import functools
import traceback
import werkzeug.exceptions

import opengui
import relations

def exceptions(endpoint):
    """
    Decorator that adds and handles a database session
    """

    @functools.wraps(endpoint)
    def wrap(*args, **kwargs):

        try:

            response = endpoint(*args, **kwargs)

        except werkzeug.exceptions.BadRequest as exception:

            response = {
                "message": exception.description
            }, 400

        except relations.ModelError as exception:

            message = str(exception)

            status_code = 404 if "none retrieved" in message else 500

            response = {
                "message": message,
            }, status_code

        except Exception as exception:

            response = {
                "message": str(exception),
                "traceback": traceback.format_exc()
            }, 500

        return response

    return wrap

class ResourceIdentity:
    """
    Intermiedate statuc type class for constructing mode information with a full resource
    """

    MODEL = None
    SINGULAR = None
    PLURAL = None
    FIELDS = None

    model = None
    fields = None

    @classmethod
    def thy(cls, self=None): # pylint: disable=too-many-branches
        """
        Base identity to be known without instantiating the class
        """

        # If self wasn't sent, we're just providing a shell of an instance

        if self is None:
            self = ResourceIdentity()
            self.__dict__.update(cls.__dict__)

        self.model = self.MODEL.thy()

        if self.SINGULAR is None:
            if hasattr(self.model, "SINGULAR") and self.model.SINGULAR is not None:
                self.SINGULAR = self.model.SINGULAR
            else:
                self.SINGULAR = self.model.NAME

        if self.PLURAL is None:
            if hasattr(self.model, "PLURAL") and self.model.PLURAL is not None:
                self.PLURAL = self.model.PLURAL
            else:
                self.PLURAL = f"{self.SINGULAR}s"

        if self.FIELDS is None:
            self.FIELDS = []

        self.fields = []
        fields = opengui.Fields(fields=self.FIELDS)

        for model_field in self.model._fields._order:

            form_field = {
                "name": model_field.name,
                "kind": model_field.kind.__name__
            }

            for attribute in ["readonly", "options", "validation"]:
                if getattr(model_field, attribute):
                    form_field[attribute] = getattr(model_field, attribute)

            if model_field.default is not None:
                form_field["default"] = model_field.default() if callable(model_field.default) else model_field.default
            elif not model_field.none:
                form_field["required"] = True

            if model_field.name in fields.names:
                form_field.update(fields[model_field.name].to_dict())

            self.fields.append(form_field)

        return self

    def endpoints(self):
        """
        Lists the endpoints this resource had
        """

        endpoints = [f"/{self.SINGULAR}"]

        if self.model.ID is not None:
            endpoints.append(f"/{self.SINGULAR}/<id>")

        return endpoints

class Resource(flask_restful.Resource, ResourceIdentity):
    """
    Base Model class for Relations Restful classes
    """

    def __init__(self, *args, **kwargs):

        super(Resource).__init__(*args, **kwargs)

        # Know thyself

        self.thy(self)

    @staticmethod
    def criteria(verify=False):
        """
        Gets criteria from the flask request
        """

        if verify and not flask.request.args and "filter" not in (flask.request.json or {}):
            raise werkzeug.exceptions.BadRequest("to confirm all, send a blank filter {}")

        criteria = {}

        if flask.request.args:
            criteria.update(flask.request.args.to_dict())

        if flask.request.json is not None and "filter" in flask.request.json:
            criteria.update(flask.request.json["filter"])

        return criteria

    @exceptions
    def options(self, id=None):
        """
        Generates form for inserts or updates of a single record
        """

        values = (flask.request.json or {}).get(self.SINGULAR)

        if id is None:

            return opengui.Fields(values=values, fields=self.fields).to_dict(), 200

        originals = dict(self.MODEL.one(**{self.model._id: id}))

        return opengui.Fields(values=values or originals, originals=originals, fields=self.fields).to_dict(), 200

    @exceptions
    def post(self):
        """
        Creates one or more models
        """

        if self.SINGULAR in (flask.request.json or {}):

            return {self.SINGULAR: dict(self.MODEL(**flask.request.json[self.SINGULAR]).create())}, 201

        if self.PLURAL in (flask.request.json or {}):

            return {self.PLURAL: [dict(model) for model in self.MODEL(flask.request.json[self.PLURAL]).create()]}, 201

        raise werkzeug.exceptions.BadRequest(f"either {self.SINGULAR} or {self.PLURAL} required")

    @exceptions
    def get(self, id=None):
        """
        Retrieves one or more models
        """

        if id is not None:
            return {self.SINGULAR: dict(self.MODEL.one(**{self.model._id: id}))}, 200

        return {self.PLURAL: [dict(model) for model in self.MODEL.many(**self.criteria())]}, 200

    @exceptions
    def patch(self, id=None):
        """
        Updates models
        """

        if self.SINGULAR not in (flask.request.json or {}) and self.PLURAL not in (flask.request.json or {}):
            raise werkzeug.exceptions.BadRequest(f"either {self.SINGULAR} or {self.PLURAL} required")

        if id is not None:

            model = self.MODEL.one(**{self.model._id: id}).set(**flask.request.json[self.SINGULAR])

        elif self.SINGULAR in flask.request.json:

            model = self.MODEL.one(**self.criteria(True)).set(**flask.request.json[self.SINGULAR])

        elif self.PLURAL in flask.request.json:

            model = self.MODEL.many(**self.criteria(True)).set(**flask.request.json[self.PLURAL])

        return {"updated": model.update()}, 202

    @exceptions
    def delete(self, id=None):
        """
        Deletes models
        """

        if id is not None:

            model = self.MODEL.one(**{self.model._id: id})

        else:

            model = self.MODEL.many(**self.criteria(True))

        return {"deleted": model.delete()}, 202
