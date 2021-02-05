import unittest
import unittest.mock
import relations.unittest
import relations_restful.unittest

import sys
import flask
import flask_restful

import relations
import relations_restful

class ResourceModel(relations.Model):
    SOURCE = "TestRestful"

class PeanutButter(ResourceModel):
    id = int
    name = str

class Jelly(ResourceModel):
    ID = None
    name = str

class Time(ResourceModel):
    id = int
    name = str

class JellyResource(relations_restful.Resource):
    MODEL = Jelly

class TimeResource(relations_restful.Resource):
    MODEL = Time

class TestRestful(relations_restful.unittest.TestCase):

    maxDiff = None

    def test_resources(self):

        self.assertEqual(relations_restful.resources(sys.modules[__name__]), [
            JellyResource,
            TimeResource
        ])

    def test_ensure(self):

        common = relations_restful.ensure(sys.modules[__name__], relations.models(sys.modules[__name__], ResourceModel))

        self.assertEqual(common[0].MODEL, PeanutButter)
        self.assertTrue(issubclass(common[0], relations_restful.Resource))

    def test_attach(self):

        source = relations.unittest.MockSource("TestRestful")

        app = flask.Flask("restful-api")
        restful = flask_restful.Api(app)

        restful.add_resource(TimeResource, '/time')

        relations_restful.attach(restful, sys.modules[__name__], relations.models(sys.modules[__name__], ResourceModel))

        api = app.test_client()

        response = api.post("/peanutbutter", json={"peanutbutter": {"name": "chunky"}})

        self.assertStatusModel(response, 201, "peanutbutter", {
            "name": "chunky"
        })

        id = response.json["peanutbutter"]["id"]

        response = api.get(f"/peanutbutter/{id}")

        self.assertStatusModel(response, 200, "peanutbutter", {
            "name": "chunky"
        })

        response = api.get(f"/peanutbutter/0")

        self.assertStatusModel(response, 404, "message", 'peanutbutter: none retrieved')

        response = api.get(f"/jelly")

        self.assertStatusValue(response, 200, "jellys", [])

        response = api.get(f"/jelly/0")

        self.assertIsNone(response.json)
        self.assertEqual(response.status_code, 404)
