import unittest
import unittest.mock
import relations.unittest
import relations_restful.unittest

import flask
import flask_restful

import ipaddress

import relations
import relations_restful


class SourceModel(relations.Model):
    SOURCE = "TestRestfulSource"

class Simple(SourceModel):
    id = int
    name = str

class Plain(SourceModel):
    ID = None
    simple_id = int
    name = str

relations.OneToMany(Simple, Plain)

class Meta(SourceModel):
    id = int
    name = str
    flag = bool
    spend = float
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

class Net(SourceModel):

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

class Unit(SourceModel):
    id = int
    name = str, {"format": "fancy"}

class Test(SourceModel):
    id = int
    unit_id = int
    name = str, {"format": "shmancy"}

class Case(SourceModel):
    id = int
    test_id = int
    name = str

relations.OneToMany(Unit, Test)
relations.OneToOne(Test, Case)

class TestSource(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        class ResourceModel(relations.Model):
            SOURCE = "TestRestfulResource"

        class Simple(ResourceModel):
            id = int
            name = str

        class Plain(ResourceModel):
            ID = None
            simple_id = int
            name = str

        relations.OneToMany(Simple, Plain)

        class SimpleResource(relations_restful.Resource):
            MODEL = Simple

        class PlainResource(relations_restful.Resource):
            MODEL = Plain

        class Meta(ResourceModel):
            id = int
            name = str
            flag = bool
            spend = float
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

        class MetaResource(relations_restful.Resource):
            MODEL = Meta

        class NetResource(relations_restful.Resource):
            MODEL = Net

        class Unit(ResourceModel):
            id = int
            name = str

        class Test(ResourceModel):
            id = int
            unit_id = int
            name = str

        class Case(ResourceModel):
            id = int
            test_id = int
            name = str

        relations.OneToMany(Unit, Test)
        relations.OneToOne(Test, Case)

        class UnitResource(relations_restful.Resource):
            MODEL = Unit

        class TestResource(relations_restful.Resource):
            MODEL = Test

        class CaseResource(relations_restful.Resource):
            MODEL = Case

        self.resource = relations.unittest.MockSource("TestRestfulResource")

        self.app = flask.Flask("source-api")
        restful = flask_restful.Api(self.app)

        restful.add_resource(SimpleResource, '/simple', '/simple/<id>')
        restful.add_resource(PlainResource, '/plain')

        restful.add_resource(MetaResource, '/meta', '/meta/<id>')
        restful.add_resource(NetResource, '/net', '/net/<id>')

        restful.add_resource(UnitResource, '/unit', '/unit/<id>')
        restful.add_resource(TestResource, '/test', '/test/<id>')
        restful.add_resource(CaseResource, '/case', '/case/<id>')

        self.source = relations_restful.Source("TestRestfulSource", "", self.app.test_client())

        def result(model, key, response):

            if key in response.json:
                return response.json[key]

            print(response.json)

        self.source.result = result

    @unittest.mock.patch("relations.SOURCES", {})
    @unittest.mock.patch("requests.Session")
    def test___init__(self, mock_session):

        source = relations_restful.Source("unit", "http://test.com", a=1)
        self.assertEqual(source.name, "unit")
        self.assertEqual(source.url, "http://test.com")
        self.assertEqual(source.session.a, 1)
        self.assertEqual(relations.SOURCES["unit"], source)

        source = relations_restful.Source("test", "http://unit.com", session="sesh")
        self.assertEqual(source.name, "test")
        self.assertEqual(source.url, "http://unit.com")
        self.assertEqual(source.session, "sesh")
        self.assertEqual(relations.SOURCES["test"], source)

    @unittest.mock.patch("relations.SOURCES", {})
    def test_result(self):

        source = relations_restful.Source("test", "http://unit.com", session="sesh")

        model = unittest.mock.MagicMock()
        model.NAME = "moded"
        model.overflow = False

        # good

        response = unittest.mock.MagicMock()
        response.status_code = 200
        response.json.return_value = {"name": "value", "overflow": True}

        self.assertEqual(source.result(model, "name", response), "value")
        self.assertTrue(model.overflow)

        # bad

        response = unittest.mock.MagicMock()
        response.status_code = 500
        response.json.return_value = {"message": "whoops"}

        self.assertRaisesRegex(relations.ModelError, "moded: whoops", source.result, model, "whatevs", response)

    def test_model_init(self):

        class Check(relations.Model):
            id = int
            name = str

        model = Check()
        self.source.model_init(model)

        self.assertEqual(model.SINGULAR, "check")
        self.assertEqual(model.PLURAL, "checks")
        self.assertEqual(model.ENDPOINT, "check")
        self.assertTrue(model._fields._names["id"].auto)

        Check.SINGULAR = "people"
        Check.PLURAL = "stuff"
        Check.ENDPOINT = "things"

        model = Check()
        self.source.model_init(model)

        self.assertEqual(model.SINGULAR, "people")
        self.assertEqual(model.PLURAL, "stuff")
        self.assertEqual(model.ENDPOINT, "things")

    def test_model_create(self):

        simple = Simple("sure")
        simple.plain.add("fine")

        simple.create()

        self.assertEqual(simple.id, 1)
        self.assertEqual(simple._action, "update")
        self.assertEqual(simple._record._action, "update")
        self.assertEqual(simple.plain[0].simple_id, 1)
        self.assertEqual(simple.plain._action, "update")
        self.assertEqual(simple.plain[0]._record._action, "update")

        simples = Simple.bulk().add("ya").create()

        self.assertEqual(simples._models, [])

        yep = Meta("yep", True, 3.50, [1, None], {"a": 1, "for": [{"1": "yep"}]}, "sure").create()
        self.assertTrue(Meta.one(yep.id).flag)

        nope = Meta("nope", False).create()
        self.assertFalse(Meta.one(nope.id).flag)

        self.assertEqual(self.resource.ids, {
            "simple": 2,
            "plain": 1,
            "meta": 2
        })

        self.assertEqual(self.resource.data, {
            "simple": {
                1: {
                    "id": 1,
                    "name": "sure"
                },
                2: {
                    "id": 2,
                    "name": "ya"
                }
            },
            "plain": {
                1: {
                    "simple_id": 1,
                    "name": "fine"
                }
            },
            "meta": {
                1: {
                    "id": 1,
                    "name": "yep",
                    "flag": True,
                    "spend": 3.50,
                    "stuff": [1, {"relations.io": {"1": "sure"}}],
                    "things": {"a": 1, "for": [{"1": "yep"}]},
                    "things__for__0___1": "yep"
                },
                2: {
                    "id": 2,
                    "name": "nope",
                    "flag": False,
                    "spend": None,
                    "stuff": [{"relations.io": {"1": None}}],
                    "things": {},
                    "things__for__0___1": None
                }
            }
        })

    def test_model_count(self):

        Unit([["stuff"], ["people"]]).create()

        self.assertEqual(Unit.many().count(), 2)

        self.assertEqual(Unit.many(name="people").count(), 1)

        self.assertEqual(Unit.many(like="p").count(), 1)

    def test_model_retrieve(self):

        Unit([["people"], ["stuff"]]).create()

        models = Unit.one(name__in=["people", "stuff"])
        self.assertRaisesRegex(relations.ModelError, "unit: more than one retrieved", models.retrieve)

        model = Unit.one(name="things")
        self.assertRaisesRegex(relations.ModelError, "unit: none retrieved", model.retrieve)

        self.assertIsNone(model.retrieve(False))

        unit = Unit.one(name="people")

        self.assertEqual(unit.id, 1)
        self.assertEqual(unit._action, "update")
        self.assertEqual(unit._record._action, "update")

        unit = Unit.one(like="p")

        self.assertEqual(unit.id, 1)
        self.assertEqual(unit._action, "update")
        self.assertEqual(unit._record._action, "update")

        unit.test.add("things")[0].case.add("persons")
        unit.update()

        model = Unit.many(test__name="things")

        self.assertEqual(model.id, [1])
        self.assertEqual(model[0]._action, "update")
        self.assertEqual(model[0]._record._action, "update")
        self.assertEqual(model[0].test[0].id, 1)
        self.assertEqual(model[0].test[0].case.name, "persons")

        self.assertEqual(Unit.many().name, ["people", "stuff"])
        self.assertEqual(Unit.many().sort("-name").name, ["stuff", "people"])
        self.assertEqual(Unit.many().sort("-name").limit(1, 1).name, ["people"])
        self.assertEqual(Unit.many().sort("-name").limit(0).name, [])
        self.assertEqual(Unit.many(name="people").limit(1).name, ["people"])

        Meta("dive", stuff=[1, 2, 3, None], things={"a": {"b": [1], "c": "sure"}, "4": 5, "for": [{"1": "yep"}]}).create()

        model = Meta.many(stuff__1=2)
        self.assertEqual(model[0].name, "dive")

        model = Meta.many(things__a__b__0=1)
        self.assertEqual(model[0].name, "dive")

        model = Meta.many(things__a__c__like="su")
        self.assertEqual(model[0].name, "dive")

        model = Meta.many(things__a__d__null=True)
        self.assertEqual(model[0].name, "dive")

        model = Meta.many(things___4=5)
        self.assertEqual(model[0].name, "dive")

        model = Meta.many(things__a__b__0__gt=1)
        self.assertEqual(len(model), 0)

        model = Meta.many(things__a__c__notlike="su")
        self.assertEqual(len(model), 0)

        model = Meta.many(things__a__d__null=False)
        self.assertEqual(len(model), 0)

        model = Meta.many(things___4=6)
        self.assertEqual(len(model), 0)

        Net(ip="1.2.3.4", subnet="1.2.3.0/24").create()
        Net().create()

        model = Net.many(like='1.2.3.')
        self.assertEqual(model[0].ip.compressed, "1.2.3.4")

        model = Net.many(ip__address__like='1.2.3.')
        self.assertEqual(model[0].ip.compressed, "1.2.3.4")

        model = Net.many(ip__value__gt=int(ipaddress.IPv4Address('1.2.3.0')))
        self.assertEqual(model[0].ip.compressed, "1.2.3.4")

        model = Net.many(subnet__address__like='1.2.3.')
        self.assertEqual(model[0].ip.compressed, "1.2.3.4")

        model = Net.many(subnet__min_value=int(ipaddress.IPv4Address('1.2.3.0')))
        self.assertEqual(model[0].ip.compressed, "1.2.3.4")

        model = Net.many(ip__address__notlike='1.2.3.')
        self.assertEqual(len(model), 0)

        model = Net.many(ip__value__lt=int(ipaddress.IPv4Address('1.2.3.0')))
        self.assertEqual(len(model), 0)

        model = Net.many(subnet__address__notlike='1.2.3.')
        self.assertEqual(len(model), 0)

        model = Net.many(subnet__max_value=int(ipaddress.IPv4Address('1.2.3.0')))
        self.assertEqual(len(model), 0)

    def test_model_labels(self):

        Unit("people").create().test.add("stuff").add("things").create()

        labels = Unit.many().labels()

        self.assertEqual(labels.id, "id")
        self.assertEqual(labels.label, ["name"])
        self.assertEqual(labels.parents, {})
        self.assertEqual(labels.format, ["fancy"])

        self.assertEqual(labels.ids, [1])
        self.assertEqual(labels.labels,{1: ["people"]})

        labels = Test.many().labels()

        self.assertEqual(labels.id, "id")
        self.assertEqual(labels.label, ["unit_id", "name"])

        self.assertEqual(labels.parents["unit_id"].id, "id")
        self.assertEqual(labels.parents["unit_id"].label, ["name"])
        self.assertEqual(labels.parents["unit_id"].parents, {})
        self.assertEqual(labels.parents["unit_id"].format, ["fancy"])

        self.assertEqual(labels.format, ["fancy", "shmancy"])

        self.assertEqual(labels.ids, [1, 2])
        self.assertEqual(labels.labels, {
            1: ["people", "stuff"],
            2: ["people", "things"]
        })

        Net(ip="1.2.3.4", subnet="1.2.3.0/24").create()

        self.assertEqual(Net.many().labels().labels, {
            1: ["1.2.3.4"]
        })

    def test_field_update(self):

        # Standard

        field = relations.Field(int, name="id")
        self.source.field_init(field)
        values = {}
        field.value = 1
        self.source.field_update(field, values)
        self.assertEqual(values, {"id": 1})

        # not changed

        values = {}
        self.source.field_update(field, values)
        self.assertEqual(values, {})

        # auto

        field = relations.Field(int, name="id", auto=True)
        self.source.field_init(field)
        values = {}
        field.value = 1
        self.source.field_update(field, values)
        self.assertEqual(values, {})

    def test_field_mass(self):

        # Standard

        field = relations.Field(int, name="id")
        self.source.field_init(field)
        values = {}
        field.value = 1
        self.source.field_update(field, values)
        self.assertEqual(values, {"id": 1})

        # not changed

        field.changed = False
        values = {}
        self.source.field_update(field, values)
        self.assertEqual(values, {})
        self.assertFalse(field.changed)

        # auto

        field = relations.Field(int, name="id", auto=True)
        self.source.field_init(field)
        values = {}
        field.value = 1
        self.source.field_update(field, values)
        self.assertEqual(values, {})

    def test_model_update(self):

        Unit([["people"], ["stuff"]]).create()

        unit = Unit.many(id=2).set(name="things")

        self.assertEqual(unit.update(), 1)

        unit = Unit.one(2)

        unit.name = "thing"
        unit.test.add("moar")

        self.assertEqual(unit.update(), 1)
        self.assertEqual(unit.name, "thing")
        self.assertEqual(unit.test[0].id, 1)
        self.assertEqual(unit.test[0].name, "moar")

        plain = Plain.one()
        self.assertRaisesRegex(relations.ModelError, "plain: nothing to update from", plain.update)

        net = Net(ip="1.2.3.4", subnet="1.2.3.0/24").create()

        Net.one(net.id).set(ip="5.6.7.8").update()
        self.assertEqual(Net.one(net.id).ip.compressed, "5.6.7.8")

    def test_model_delete(self):

        unit = Unit("people")
        unit.test.add("stuff").add("things")
        unit.create()

        self.assertEqual(Test.one(id=2).delete(), 1)
        self.assertEqual(len(Test.many()), 1)

        self.assertEqual(Unit.one(1).test.delete(), 1)
        self.assertEqual(Unit.one(1).retrieve().delete(), 1)
        self.assertEqual(len(Unit.many()), 0)
        self.assertEqual(len(Test.many()), 0)

        plain = Plain(0, "nope").create()
        self.assertRaisesRegex(relations.ModelError, "plain: nothing to delete from", plain.delete)
