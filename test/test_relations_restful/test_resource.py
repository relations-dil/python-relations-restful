import unittest
import unittest.mock
import relations.unittest
import relations_restful.unittest

import flask
import flask_restful
import werkzeug.exceptions

import opengui
import ipaddress

import relations
import relations_restful


class ResourceModel(relations.Model):
    SOURCE = "TestRestfulResource"

class Simple(ResourceModel):
    id = int
    name = str
    CHUNK = 2

class Plain(ResourceModel):
    ID = None
    simple_id = int
    name = str

relations.OneToMany(Simple, Plain)

class Meta(ResourceModel):
    id = int
    name = str
    flag = bool
    spend = float
    people = set
    stuff = list
    things = dict, {"extract": "for__0___1"}
    push = str, {"inject": "stuff__-1__relations.io___1"}

def subnet_attr(values, value):

    values["address"] = str(value)
    min_ip = value[0]
    max_ip = value[-1]
    values["min_address"] = str(min_ip)
    values["min_value"] = int(min_ip)
    values["max_address"] = str(max_ip)
    values["max_value"] = int(max_ip)

class Net(ResourceModel):

    id = int
    ip = ipaddress.IPv4Address, {
        "attr": {"compressed": "address", "__int__": "value"},
        "init": "address",
        "label": "address",
        "extract": {"address": str, "value": int}
    }
    subnet = ipaddress.IPv4Network, {
        "attr": subnet_attr,
        "init": "address",
        "label": "address"
    }

    LABEL = "ip__address"
    INDEX = "ip__value"

class SimpleResource(relations_restful.Resource):
    MODEL = Simple

class PlainResource(relations_restful.Resource):
    MODEL = Plain

class MetaResource(relations_restful.Resource):
    MODEL = Meta

class NetResource(relations_restful.Resource):
    MODEL = Net

class TestRestful(relations_restful.unittest.TestCase):

    def setUp(self):

        self.source = relations.unittest.MockSource("TestRestfulResource")

        self.app = flask.Flask("resource-api")
        restful = flask_restful.Api(self.app)

        restful.add_resource(SimpleResource, *SimpleResource.thy().endpoints())
        restful.add_resource(PlainResource, *PlainResource.thy().endpoints())
        restful.add_resource(MetaResource, *MetaResource.thy().endpoints())
        restful.add_resource(NetResource, *NetResource.thy().endpoints())

        self.api = self.app.test_client()


class TestExceptions(TestRestful):

    @unittest.mock.patch("traceback.format_exc")
    def test_exceptions(self, mock_traceback):

        @relations_restful.exceptions
        def good():
            return {"good": True}

        self.app.add_url_rule('/good', 'good', good)

        self.assertStatusValue(self.api.get("/good"), 200, "good", True)

        @relations_restful.exceptions
        def bad():
            raise werkzeug.exceptions.BadRequest("nope")

        self.app.add_url_rule('/bad', 'bad', bad)

        self.assertStatusValue(self.api.get("/bad"), 400, "message", "nope")

        @relations_restful.exceptions
        def ugly():
            raise Exception("whoops")

        mock_traceback.return_value = "adaisy"

        self.app.add_url_rule('/ugly', 'ugly', ugly)

        response = self.api.get("/ugly")

        self.assertStatusValue(response, 500, "message", "whoops")
        self.assertStatusValue(response, 500, "traceback", "adaisy")

        @relations_restful.exceptions
        def missing():
            raise relations.ModelError(Simple(), "none retrieved")

        self.app.add_url_rule('/missing', 'missing', missing)

        self.assertStatusValue(self.api.get("/missing"), 404, "message", "simple: none retrieved")

        @relations_restful.exceptions
        def broken():
            raise relations.ModelError(Simple(), "broken query")

        self.app.add_url_rule('/broken', 'broken', broken)

        self.assertStatusValue(self.api.get("/broken"), 500, "message", "simple: broken query")


class Whoops(relations.Model):
    id = int
    name = str

class WhoopsResource(relations_restful.Resource):
    MODEL = Whoops

class TestResourceError(unittest.TestCase):

    maxDiff = None

    def test___init__(self):

        error = relations_restful.ResourceError("unittest", "oops")

        self.assertEqual(error.resource, "unittest")
        self.assertEqual(error.message, "oops")

    def test___str__(self):

        error = relations_restful.ResourceError(WhoopsResource(), "adaisy")

        self.assertEqual(str(error), "WhoopsResource: adaisy")


class TestResourceIdentity(TestRestful):

    def test_thy(self):

        class Init(ResourceModel):
            id = int
            name = str
            status = str,"good"
            meta = dict
            push = str, {"inject": "meta__a__-1__relations.io___1"}
            ip = ipaddress.IPv4Address, {
                "attr": {"compressed": "address", "__int__": "value"},
                "init": "address",
                "label": "address"
            }

        class InitResource(relations_restful.ResourceIdentity):
            MODEL = Init

        resource = InitResource.thy()
        self.assertEqual(resource.SINGULAR, "init")
        self.assertEqual(resource.PLURAL, "inits")
        self.assertEqual(resource.FIELDS, [])
        self.assertEqual(resource._fields, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            },
            {
                "name": "status",
                "kind": "str",
                "default": "good"
            },
            {
                "name": "meta",
                "kind": "dict",
                "default": {}
            },
            {
                "name": "push",
                "kind": "str",
                "inject": "meta__a__-1__relations.io___1"
            },
            {
                "name": "ip",
                "kind": "IPv4Address",
                "init": {"address": "address"}
            }
        ])
        self.assertEqual(resource.LIST, ['id', 'name'])

        Init.SINGULAR = "inity"
        Init.LABEL = ["name", "status"]
        InitResource.FIELDS = [
            {
                "name": "name",
                "kind": "str",
                "options": ["few"],
                "required": True
            }
        ]
        resource = InitResource.thy()
        self.assertEqual(resource.SINGULAR, "inity")
        self.assertEqual(resource.PLURAL, "initys")
        self.assertEqual(resource._fields, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True
            },
            {
                "name": "name",
                "kind": "str",
                "options": ["few"],
                "required": True
            },
            {
                "name": "status",
                "kind": "str",
                "default": "good"
            },
            {
                "name": "meta",
                "kind": "dict",
                "default": {}
            },
            {
                "name": "push",
                "kind": "str",
                "inject": "meta__a__-1__relations.io___1"
            },
            {
                "name": "ip",
                "kind": "IPv4Address",
                "init": {"address": "address"}
            }
        ])
        self.assertEqual(resource.LIST, ['id', 'name', 'status'])

        Init.PLURAL = "inities"
        InitResource.FIELDS = [
            {
                "name": "name",
                "kind": "str",
                "validation": "gone"
            }
        ]
        resource = InitResource.thy()
        self.assertEqual(resource.SINGULAR, "inity")
        self.assertEqual(resource.PLURAL, "inities")
        self.assertEqual(resource._fields, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True
            },
            {
                "name": "name",
                "kind": "str",
                "validation": "gone",
                "required": True
            },
            {
                "name": "status",
                "kind": "str",
                "default": "good"
            },
            {
                "name": "meta",
                "kind": "dict",
                "default": {}
            },
            {
                "name": "push",
                "kind": "str",
                "inject": "meta__a__-1__relations.io___1"
            },
            {
                "name": "ip",
                "kind": "IPv4Address",
                "init": {"address": "address"}
            }
        ])

        InitResource.SINGULAR = "initee"
        resource = InitResource.thy()
        self.assertEqual(resource.SINGULAR, "initee")
        self.assertEqual(resource.PLURAL, "inities")

        InitResource.PLURAL = "initiease"
        resource = InitResource.thy()
        self.assertEqual(resource.SINGULAR, "initee")
        self.assertEqual(resource.PLURAL, "initiease")

        InitResource.LIST = ["name"]
        resource = InitResource.thy()
        self.assertEqual(resource.SINGULAR, "initee")
        self.assertEqual(resource.PLURAL, "initiease")
        self.assertEqual(resource.LIST, ['name'])

        InitResource.LIST = ["nope"]
        self.assertRaisesRegex(relations_restful.ResourceError, "cannot find field nope from list", InitResource.thy)

    def test_endpoints(self):

        self.assertEqual(SimpleResource.thy().endpoints(), ["/simple", "/simple/<id>"])
        self.assertEqual(PlainResource.thy().endpoints(), ["/plain"])

class TestResource(TestRestful):

    def test___init__(self):

        class Init(ResourceModel):
            id = int
            name = str
            status = str,"good"
            meta = dict

        class InitResource(relations_restful.Resource):
            MODEL = Init

        resource = InitResource()
        self.assertEqual(resource.SINGULAR, "init")
        self.assertEqual(resource.PLURAL, "inits")
        self.assertEqual(resource.FIELDS, [])
        self.assertEqual(resource._fields, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            },
            {
                "name": "status",
                "kind": "str",
                "default": "good"
            },
            {
                "name": "meta",
                "kind": "dict",
                "default": {}
            }
        ])

    def test_criteria(self):

        verify = True

        @relations_restful.exceptions
        def criteria():
            return {"criteria": relations_restful.Resource.criteria(verify)}

        self.app.add_url_rule('/criteria', 'criteria', criteria)

        response = self.api.get("/criteria")
        self.assertStatusValue(response, 400, "message", "to confirm all, send a blank filter {}")

        verify = False
        response = self.api.get("/criteria")
        self.assertStatusValue(response, 200, "criteria", {})

        response = self.api.get("/criteria?a=1&sort=a&limit=2")
        self.assertStatusValue(response, 200, "criteria", {"a": "1"})

        response = self.api.get("/criteria?a=1", json={"filter": {"a": 2}})
        self.assertStatusValue(response, 200, "criteria", {"a": 2})

    def test_sort(self):

        @relations_restful.exceptions
        def sort():
            return {"sort": relations_restful.Resource.sort()}

        self.app.add_url_rule('/sort', 'sort', sort)

        response = self.api.get("/sort")
        self.assertStatusValue(response, 200, "sort", [])

        response = self.api.get("/sort?sort=a,-b")
        self.assertStatusValue(response, 200, "sort", ["a", "-b"])

        response = self.api.get("/sort?sort=-a", json={"sort": ["b", "+c"]})
        self.assertStatusValue(response, 200, "sort", ["-a", "b", "+c"])

    def test_limit(self):

        @relations_restful.exceptions
        def limit():
            return {"limit": relations_restful.Resource.limit()}

        self.app.add_url_rule('/limit', 'limit', limit)

        response = self.api.get("/limit")
        self.assertStatusValue(response, 200, "limit", {})

        response = self.api.get("/limit?limit__per_page=1&limit__page=2")
        self.assertStatusValue(response, 200, "limit", {"per_page": 1, "page": 2})

        response = self.api.get("/limit?limit=1", json={"limit": {"per_page": "2", "page": 3}})
        self.assertStatusValue(response, 200, "limit", {"limit": 1, "per_page": 2, "page": 3})

    def test_count(self):

        @relations_restful.exceptions
        def count():
            return {"count": relations_restful.Resource.count()}

        self.app.add_url_rule('/count', 'count', count)

        response = self.api.get("/count")
        self.assertStatusValue(response, 200, "count", False)

        response = self.api.get("/count?count=yes")
        self.assertStatusValue(response, 200, "count", True)

        response = self.api.get("/count", json={"count": False})
        self.assertStatusValue(response, 200, "count", False)

        response = self.api.get("/count", json={"count": "FALSE"})
        self.assertStatusValue(response, 200, "count", False)

        response = self.api.get("/count", json={"count": "0"})
        self.assertStatusValue(response, 200, "count", False)

        response = self.api.get("/count", json={"count": "no"})
        self.assertStatusValue(response, 200, "count", False)

    def test_fields(self):

        self.assertEqual(SimpleResource().fields(
            likes={},
            values={
                "name": "ya"
            },
            originals={
                "name": "sure"
            }
        ).to_list(), [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
            },
            {
                "name": "name",
                "kind": "str",
                "required": True,
                "value": "ya",
                "original": "sure"
            }
        ])

        self.assertEqual(SimpleResource().fields(
            likes={},
            values={},
            originals={
                "name": "sure"
            }
        ).to_list(), [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
            },
            {
                "name": "name",
                "kind": "str",
                "required": True,
                "original": "sure"
            }
        ])

        Simple("ya").create()

        self.assertEqual(PlainResource().fields(
            likes={
                "simple_id": "y"
            },
            values={}
        ).to_list(), [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [1],
                "labels": {
                    1: ["ya"]
                },
                "like": "y",
                "format": [None],
                "overflow": False,
                "required": True
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ])

        self.assertEqual(PlainResource().fields(
            likes={
                "simple_id": "n"
            },
            values={
                "simple_id": 1
            }
        ).to_list(), [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [],
                "labels": {},
                "like": "n",
                "format": [None],
                "overflow": False,
                "required": True,
                "value": 1
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ])

        Simple("sure").create()
        Simple("whatevs").create()

        self.assertEqual(PlainResource().fields(
            likes={},
            values={}
        ).to_list(), [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [2, 3],
                "labels": {
                    2: ["sure"],
                    3: ["whatevs"]
                },
                "format": [None],
                "overflow": True,
                "required": True
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ])

        self.assertEqual(PlainResource().fields(
            likes={},
            values={},
            originals={
                "simple_id": 1
            }
        ).to_list(), [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [1],
                "labels": {
                    1: ["ya"]
                },
                "format": [None],
                "overflow": True,
                "required": True,
                "original": 1
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ])

        self.assertEqual(PlainResource().fields(
            likes={},
            values={
                "simple_id": 1
            }
        ).to_list(), [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [1],
                "labels": {
                    1: ["ya"]
                },
                "format": [None],
                "overflow": True,
                "required": True,
                "value": 1
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ])

    def test_formats(self):

        Simple("ya").create().plain.add("sure").create()

        Simple("whatevs").create()

        self.assertEqual(SimpleResource().formats(Simple.many()), {})

        self.assertEqual(PlainResource().formats(Plain.many()), {
            "simple_id": {
                "labels": {1: ["ya"]},
                "format": [None]
            }
        })

        self.assertEqual(PlainResource().formats(Plain.many()), {
            "simple_id": {
                "labels": {1: ["ya"]},
                "format": [None]
            }
        })

        class Advanced(ResourceModel):
            id = int
            name = str
            status = ["good", "bad"]
            created = int, {"format": "datetime"}

        class AdvancedResource(relations_restful.Resource):

            MODEL = Advanced

            FIELDS = [
                {
                    "name": "status",
                    "labels": {
                        "good": "Good",
                        "bad": "Bad"
                    }
                }
            ]

        self.assertEqual(AdvancedResource().formats(Advanced.many()), {
            "status": {
                "labels": {
                    "good": "Good",
                    "bad": "Bad"
                },
            },
            "created": {
                "format": ["datetime"]
            }
        })

    def test_options(self):

        response = self.api.options("/simple")
        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ], errors=[])

        id = self.api.post("/simple", json={"simple": {"name": "ya"}}).json["simple"]["id"]

        response = self.api.options(f"/simple/{id}")
        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
                "original": id
            },
            {
                "name": "name",
                "kind": "str",
                "required": True,
                "original": "ya"
            }
        ], errors=[])

        response = self.api.options(f"/simple/{id}", json={"simple": {"name": "sure"}})
        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
                "original": id
            },
            {
                "name": "name",
                "kind": "str",
                "required": True,
                "original": "ya",
                "value": "sure"
            }
        ], errors=[])

        response = self.api.options(f"/plain", json={"likes": {"simple_id": "y"}})
        self.assertStatusFields(response, 200, [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [1],
                "labels": {
                    '1': ["ya"]
                },
                "like": "y",
                "format": [None],
                "overflow": False,
                "required": True
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ], errors=[])

        response = self.api.options(f"/plain", json={"likes": {"simple_id": "n"}})
        self.assertStatusFields(response, 200, [
            {
                "name": "simple_id",
                "kind": "int",
                "options": [],
                "labels": {},
                "like": "n",
                "format": [None],
                "overflow": False,
                "required": True
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            }
        ], errors=[])

        id = self.api.post("/net", json={"net": {"ip": "1.2.3.4", "subnet": "1.2.3.0/24"}}).json["net"]["id"]

        response = self.api.options(f"/net/{id}")
        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True,
                "original": 1
            },
            {
                "name": "ip",
                "kind": "IPv4Address",
                "original": {
                    "address": "1.2.3.4",
                    "value": 16909060
                },
                "init": {"address": "address"}
            },
            {
                "name": "subnet",
                "kind": "IPv4Network",
                "original": {
                    "address": "1.2.3.0/24",
                    "min_address": "1.2.3.0",
                    "min_value": 16909056,
                    "max_address": "1.2.3.255",
                    "max_value": 16909311
                },
                "init": {"address": "address"}
            }
        ], errors=[])

        response = self.api.options("/meta")
        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "kind": "int",
                "readonly": True
            },
            {
                "name": "name",
                "kind": "str",
                "required": True
            },
            {
                "name": "flag",
                "kind": "bool"
            },
            {
                "name": "spend",
                "kind": "float"
            },
            {
                "name": "people",
                "kind": "set",
                "default": []
            },
            {
                "name": "stuff",
                "kind": "list",
                "default": []
            },
            {
                "name": "things",
                "kind": "dict",
                "default": {}
            },
            {
                "name": "push",
                "kind": "str",
                "inject": "stuff__-1__relations.io___1"
            }
        ], errors=[])

    def test_post(self):

        response = self.api.post("/simple")
        self.assertStatusValue(response, 400, "message", "either simple or simples required")

        response = self.api.post("/simple", json={"simple": {"name": "ya"}})
        self.assertStatusModel(response, 201, "simple", {"name": "ya"})
        simple = Simple.one(id=response.json["simple"]["id"])
        self.assertEqual(simple.name, "ya")

        response = self.api.post("/plain", json={"plains": [{"name": "sure"}]})
        self.assertStatusModel(response, 201, "plains", [{"name": "sure"}])
        self.assertEqual(Plain.one().name, "sure")

        response = self.api.post("/simple", json={"filter": {"name": "ya"}})
        self.assertStatusModel(response, 200, "simples", [{"id": simple.id, "name": "ya"}])

        response = self.api.post("/simple", json={"filter": {"name": "ya"}, "count": True})
        self.assertStatusModel(response, 200, "simples", 1)

    def test_get(self):

        simple = Simple("ya").create()
        simple.plain.add("whatevs").create()

        response = self.api.get(f"/simple")
        self.assertStatusModel(response, 200, "simples", [{"id": simple.id, "name": "ya"}])
        self.assertStatusValue(response, 200, "formats", {})

        response = self.api.get(f"/plain")
        self.assertStatusModel(response, 200, "plains", [{"simple_id": simple.id, "name": "whatevs"}])
        self.assertStatusValue(response, 200, "formats", {
            "simple_id": {
                "labels": {'1': ["ya"]},
                "format": [None]
            }
        })

        response = self.api.get(f"/simple/{simple.id}")
        self.assertStatusModel(response, 200, "simple", {"id": simple.id, "name": "ya"})

        response = self.api.get("/simple", json={"filter": {"name": "ya"}})
        self.assertStatusModel(response, 200, "simples", [{"id": simple.id, "name": "ya"}])
        self.assertStatusValue(response, 200, "overflow", False)

        response = self.api.get("/simple", json={"filter": {"name": "no"}})
        self.assertStatusModel(response, 200, "simples", [])
        self.assertStatusValue(response, 200, "overflow", False)

        Simple("sure").create()
        Simple("fine").create()

        response = self.api.get("/simple", json={"filter": {"like": "y"}})
        self.assertStatusModels(response, 200, "simples", [{"id": simple.id, "name": "ya"}])
        self.assertStatusValue(response, 200, "overflow", False)

        response = self.api.get("/simple?limit=1&limit__start=1")
        self.assertStatusModels(response, 200, "simples", [{"name": "sure"}])
        self.assertStatusValue(response, 200, "overflow", True)

        response = self.api.get("/simple?limit__per_page=1&limit__page=3")
        self.assertStatusModels(response, 200, "simples", [{"name": "ya"}])
        self.assertStatusValue(response, 200, "overflow", True)
        self.assertStatusValue(response, 200, "formats", {})

        simples = Simple.bulk()

        for name in range(3):
            simples.add(name)

        simples.create()

        self.assertEqual(self.api.get("/simple?count=yes").json["simples"], 6)
        self.assertEqual(self.api.get("/simple", json={"count": True}).json["simples"], 6)

    def test_patch(self):

        response = self.api.patch("/simple")
        self.assertStatusValue(response, 400, "message", "either simple or simples required")

        response = self.api.patch(f"/simple", json={"simple": {"name": "yep"}})
        self.assertStatusModel(response, 400, "message", "to confirm all, send a blank filter {}")

        simple = Simple("ya").create()
        response = self.api.patch(f"/simple/{simple.id}", json={"simple": {"name": "yep"}})
        self.assertStatusModel(response, 202, "updated", 1)

        response = self.api.patch("/simple", json={"filter": {"name": "yep"}, "simple": {"name": "sure"}})
        self.assertStatusModel(response, 202, "updated", 1)

        response = self.api.patch("/simple", json={"filter": {"name": "sure"}, "simples": {"name": "whatever"}})
        self.assertStatusModel(response, 202, "updated", 1)

        response = self.api.patch("/simple", json={"filter": {"name": "no"}, "simples": {}})
        self.assertStatusModel(response, 202, "updated", 0)

    def test_delete(self):

        response = self.api.delete(f"/simple")
        self.assertStatusModel(response, 400, "message", "to confirm all, send a blank filter {}")

        simple = Simple("ya").create()
        response = self.api.delete(f"/simple/{simple.id}")
        self.assertStatusModel(response, 202, "deleted", 1)

        simple = Simple("sure").create()
        response = self.api.delete("/simple", json={"filter": {"name": "sure"}})
        self.assertStatusModel(response, 202, "deleted", 1)

        response = self.api.delete("/simple", json={"filter": {"name": "no"}})
        self.assertStatusModel(response, 202, "deleted", 0)
