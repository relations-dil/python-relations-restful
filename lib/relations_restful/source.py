"""
Source module for RESTful backends
"""

# pylint: disable=arguments-differ

import requests
import relations

class Source(relations.Source):
    """
    Source with a RESTful backend
    """

    url = None
    session = None

    def __init__(self, name, url, session=None, **kwargs): # pylint: disable=unused-argument

        self.url = url

        if session is not None:
            self.session = session
        else:
            self.session = requests.Session()
            for key, arg in kwargs.items():
                if key not in ["name", "url"]:
                    setattr(self.session, key, arg)

    @staticmethod
    def result(model, key, response):
        """
        Checks a response and returns the result
        """

        if response.status_code >= 400:
            raise relations.ModelError(model, response.json().get("message", "API Error"))

        return response.json()[key]

    def model_init(self, model):
        """
        Init the model
        """

        self.record_init(model._fields)

        self.ensure_attribute(model, "SINGULAR")
        self.ensure_attribute(model, "PLURAL")
        self.ensure_attribute(model, "ENDPOINT")

        if model.SINGULAR is None:
            model.SINGULAR = model.NAME

        if model.PLURAL is None:
            model.PLURAL = f"{model.SINGULAR}s"

        if model.ENDPOINT is None:
            model.ENDPOINT = model.SINGULAR

        if model._id is not None and model._fields._names[model._id].readonly is None:
            model._fields._names[model._id].readonly = True

    def model_create(self, model):
        """
        Executes the create
        """

        models = model._each("create")
        values = []

        for creating in models:
            values.append(creating._record.write({}))

        records = self.result(model, model.PLURAL, self.session.post(f"{self.url}/{model.ENDPOINT}", json={model.PLURAL: values}))

        for index, creating in enumerate(models):

            if model._id is not None and model._fields._names[model._id].readonly:
                creating[model._id] = records[index][model._fields._names[model._id].store]

            for parent_child in creating.CHILDREN:
                if creating._children.get(parent_child):
                    creating._children[parent_child].create()

            creating._action = "update"
            creating._record._action = "update"

        model._action = "update"

        return model

    def field_retrieve(self, field, criteria):
        """
        Adds critera to the filter
        """

        for operator, value in (field.criteria or {}).items():
            criteria[f"{field.name}__{operator}"] = value

    def model_retrieve(self, model, verify=True):
        """
        Executes the retrieve
        """

        model._collate()

        criteria = {}
        self.record_retrieve(model._record, criteria)

        matches = self.result(model, model.PLURAL, self.session.get(f"{self.url}/{model.ENDPOINT}", json={"filter": criteria}))

        if model._mode == "one" and len(matches) > 1:
            raise relations.ModelError(model, "more than one retrieved")

        if model._mode == "one" and model._role != "child":

            if len(matches) < 1:

                if verify:
                    raise relations.ModelError(model, "none retrieved")
                return None

            model._record = model._build("update", _read=matches[0])

        else:

            model._models = []

            for match in matches:
                model._models.append(model.__class__(_read=match))

            model._record = None

        model._action = "update"

        return model

    def field_update(self, field, values, changed=None):
        """
        Updates values with the field's that changed
        """

        if not field.readonly and (changed is None or field.changed == changed):
            values[field.name] = field.value
            field.changed = False

    def model_update(self, model):
        """
        Executes the update
        """

        # If the overall model is retrieving and the record has values set

        updated = 0

        if model._action == "retrieve" and model._record._action == "update":

            criteria = {}
            self.record_retrieve(model._record, criteria)

            values = {}
            self.record_update(model._record, values, changed=True)

            updated += self.result(model, "updated", self.session.patch(
                f"{self.url}/{model.ENDPOINT}", json={"filter": criteria, model.PLURAL: values})
            )

        elif model._id:

            for updating in model._each("update"):

                values = {}
                self.record_update(updating._record, values)

                updated += self.result(updating, "updated", self.session.patch(
                    f"{self.url}/{model.ENDPOINT}/{updating[model._id]}", json={model.SINGULAR: values})
                )

                for parent_child in updating.CHILDREN:
                    if updating._children.get(parent_child):
                        updating._children[parent_child].create().update()

        else:

            raise relations.ModelError(model, "nothing to update from")

        return updated

    def model_delete(self, model):
        """
        Executes the delete
        """

        criteria = {}

        if model._action == "retrieve":

            self.record_retrieve(model._record, criteria)

        elif model._id:

            criterion = f"{model._id}__in"
            criteria[criterion] = []

            for deleting in model._each():
                criteria[criterion].append(deleting[model._id])
                deleting._action = "create"

            model._action = "create"

        else:

            raise relations.ModelError(model, "nothing to delete from")

        return self.result(model, "deleted", self.session.delete(f"{self.url}/{model.ENDPOINT}", json={"filter": criteria}))
