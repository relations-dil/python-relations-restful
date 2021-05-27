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

class ResourceError(Exception):
    """
    Generic resource Error for easier tracing
    """

    def __init__(self, resource, message):

        self.resource = resource
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """
        Might want to mention the resource and info about it
        """
        return f"{self.resource.__class__.__name__}: {self.message}"

class ResourceIdentity:
    """
    Intermediate static type class for constructing mode information with a full resource
    """

    MODEL = None
    SINGULAR = None
    PLURAL = None
    FIELDS = None
    LIST = None

    _model = None
    _fields = None

    @classmethod
    def thy(cls, self=None): # pylint: disable=too-many-branches
        """
        Base identity to be known without instantiating the class
        """

        # If self wasn't sent, we're just providing a shell of an instance

        if self is None:
            self = ResourceIdentity()
            self.__dict__.update(cls.__dict__)

        self._model = self.MODEL.thy()

        if self.SINGULAR is None:
            if hasattr(self._model, "SINGULAR") and self._model.SINGULAR is not None:
                self.SINGULAR = self._model.SINGULAR
            else:
                self.SINGULAR = self._model.NAME

        if self.PLURAL is None:
            if hasattr(self._model, "PLURAL") and self._model.PLURAL is not None:
                self.PLURAL = self._model.PLURAL
            else:
                self.PLURAL = f"{self.SINGULAR}s"

        if self.FIELDS is None:
            self.FIELDS = []

        self._fields = []
        fields = opengui.Fields(fields=self.FIELDS)

        for model_field in self._model._fields._order:

            form_field = {
                "name": model_field.name,
                "kind": model_field.kind.__name__
            }

            for attribute in ["readonly", "options", "validation"]:
                if getattr(model_field, attribute):
                    form_field[attribute] = getattr(model_field, attribute)

            if model_field.default is not None:
                form_field["default"] = model_field.default() if callable(model_field.default) else model_field.default
            elif not model_field.none or model_field.name in self._model._label:
                form_field["required"] = True

            if model_field.name in fields.names:
                form_field.update(fields[model_field.name].to_dict())

            self._fields.append(form_field)

        if self.LIST is None:
            self.LIST = list(self._model._list)

        # Make sure all the list checks out

        for field in self.LIST:
            if field not in self._model._fields:
                raise ResourceError(self, f"cannot find field {field} from list")

        return self

    def endpoints(self):
        """
        Lists the endpoints this resource had
        """

        endpoints = [f"/{self.SINGULAR}"]

        if self._model.ID is not None:
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
            criteria.update({
                name: value
                for name, value in flask.request.args.to_dict().items()
                if not name.startswith("limit") and name != "sort"
            })

        if flask.request.json is not None and "filter" in flask.request.json:
            criteria.update(flask.request.json["filter"])

        return criteria

    @staticmethod
    def sort():
        """
        Gets soirt from the flask request
        """

        sort = []

        if flask.request.args and 'sort' in flask.request.args:
            sort.extend(flask.request.args['sort'].split(','))

        if flask.request.json is not None and "sort" in flask.request.json:
            sort.extend(flask.request.json['sort'])

        return sort

    @staticmethod
    def limit():
        """
        Gets limit from the flask request
        """

        limit = {}

        if flask.request.args:
            limit.update({
                name.split('__')[-1]: int(value)
                for name, value in flask.request.args.to_dict().items()
                if name.startswith("limit")
            })

        if flask.request.json is not None and "limit" in flask.request.json:
            limit.update({name: int(value) for name, value in flask.request.json["limit"].items()})

        return limit

    def fields(self, likes, values, originals=None):
        """
        Apply options and labels to fields
        """

        fields = opengui.Fields(values=values, originals=originals, fields=self._fields)

        for field in fields:
            relation = self._model._ancestor(field.name)
            if relation is not None:
                like = {"like": likes[name] for name in likes if name == field.name}
                parent = relation.Parent.many(**like).limit()
                labels = parent.labels()

                field.content["format"] = labels.format
                field.content["overflow"] = parent.overflow

                value = field.value if field.value is not None else field.original

                if (not like and value is not None and value not in labels):
                    labels = relation.Parent.one(**{relation.parent_field: value}).labels()
                    field.content["overflow"] = True

                field.options = labels.ids
                field.content["labels"] = labels.labels

                field.content.update(like)

        return fields

    def formats(self, model):
        """
        Generate all the formats including parent lookups
        """

        formats = {}

        fields = opengui.Fields(fields=self._fields)

        for field in model._fields._order:
            relation = model._ancestor(field.name)
            if relation is not None:
                labels = relation.Parent.many(**{f"{relation.parent_field}__in": model[field.name]}).labels()
                formats[field.name] = {
                    "labels": labels.labels,
                    "format": labels.format
                }
            elif field.format is not None or "labels" in fields[field.name].content:
                formats[field.name] = {}
                if field.format is not None:
                    formats[field.name]["format"] = field.format
                if  "labels" in fields[field.name].content:
                    formats[field.name]["labels"] = fields[field.name].content["labels"]

        return formats

    @exceptions
    def options(self, id=None):
        """
        Generates form for inserts or updates of a single record
        """

        values = (flask.request.json or {}).get(self.SINGULAR)
        likes = (flask.request.json or {}).get("likes", {})

        if id is None:

            return self.fields(likes, values).to_dict(), 200

        originals = dict(self.MODEL.one(**{self._model._id: id}))

        return self.fields(likes, values, originals).to_dict(), 200

    @exceptions
    def post(self):
        """
        Creates one or more models
        """

        if "filter" in (flask.request.json or {}):

            return self.get()

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
            model = self.MODEL.one(**{self._model._id: id})
            return {self.SINGULAR: dict(model), "formats": self.formats(model)}

        models = self.MODEL.many(**self.criteria()).sort(*self.sort()).limit(**self.limit())

        return {self.PLURAL: [dict(model) for model in models], "overflow": models.overflow, "formats": self.formats(models)}, 200

    @exceptions
    def patch(self, id=None):
        """
        Updates models
        """

        if self.SINGULAR not in (flask.request.json or {}) and self.PLURAL not in (flask.request.json or {}):
            raise werkzeug.exceptions.BadRequest(f"either {self.SINGULAR} or {self.PLURAL} required")

        if id is not None:

            model = self.MODEL.one(**{self._model._id: id}).set(**flask.request.json[self.SINGULAR])

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

            model = self.MODEL.one(**{self._model._id: id})

        else:

            model = self.MODEL.many(**self.criteria(True))

        return {"deleted": model.delete()}, 202
