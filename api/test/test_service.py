import unittest
import unittest.mock
import freezegun

import json
import fnmatch

import yaml
import flask_restful

import opengui

import service


class MockRedis:

    def __init__(self, host, **kwargs):

        self.host = host

        self.data = {}
        self.expires = {}
        self.messages = []

        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __str__(self):

        return f"MockRedis<host={self.host},port={self.port}>"

    def get(self, key):

        return self.data.get(key)

    def set(self, key, value, ex=None):

        self.data[key] = value
        self.expires[key] = ex

    def lpush(self, key, value):

        self.data.setdefault(key, [])
        self.data[key].append(value)

    def keys(self, pattern):

        for key in sorted(self.data.keys()):
            if fnmatch.fnmatch(key, pattern):
                yield key

    def delete(self, key):

        if key in self.data:
            del self.data[key]

        if key in self.expires:
            del self.expires[key]


class TestOptions(unittest.TestCase):

    maxDiff = None

    @unittest.mock.patch.dict(service.Options.creds, {})
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch('service.open', create=True)
    def test_config(self, mock_open, mock_glob):

        mock_glob.return_value = ["what/options_people.json"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='{"stuff": "things"}').return_value
        ]

        service.Options.config()

        self.assertEqual(service.Options.creds, {
            "people": {
                "stuff": "things",
                "verify": True
            }
        })

    @unittest.mock.patch.dict(service.Options.creds, {
        "default": {
            "url": "arcade",
            "verify": True
        }
    })
    def test___init__(self):

            # defaults

            options = service.Options({})

            self.assertEqual(options.url, "arcade")
            self.assertEqual(options.verify, True)
            self.assertEqual(options.method, "GET")
            self.assertEqual(options.path, "")
            self.assertEqual(options.params, {})
            self.assertEqual(options.body, {})
            self.assertEqual(options.results, "")
            self.assertEqual(options.option, "")
            self.assertEqual(options.title, "")

            # creds

            service.Options.creds["credible"] = {
                "url": "fire",
                "verify": False,
                "method": "POST",
                "path": "long",
                "headers": {
                    "yes": "sah"
                },
                "params": {
                    "hoo": "boy"
                },
                "body": {
                    "gaw": "dam"
                },
                "results": "people",
                "option": "stuff",
                "title": "things"
            }

            data = {
                "creds": "credible"
            }

            options = service.Options(data)

            self.assertEqual(options.url, "fire")
            self.assertEqual(options.verify, False)
            self.assertEqual(options.method, "POST")
            self.assertEqual(options.path, "long")
            self.assertEqual(options.params, {"hoo": "boy"})
            self.assertEqual(options.body, {"gaw": "dam"})
            self.assertEqual(options.results, "people")
            self.assertEqual(options.option, "stuff")
            self.assertEqual(options.title, "things")

            self.assertEqual(options.session.headers["yes"], "sah")

            # data

            data = {
                "creds": "credible",
                "url": "disco",
                "username": "me",
                "password": "sh",
                "token": "ring"
            }

            options = service.Options(data)

            self.assertEqual(options.url, "disco")
            self.assertEqual(options.verify, False)
            self.assertEqual(options.method, "POST")
            self.assertEqual(options.path, "long")
            self.assertEqual(options.params, {"hoo": "boy"})
            self.assertEqual(options.body, {"gaw": "dam"})
            self.assertEqual(options.results, "people")
            self.assertEqual(options.option, "stuff")
            self.assertEqual(options.title, "things")

            self.assertEqual(options.session.headers["yes"], "sah")
            self.assertEqual(options.session.auth, ("me", "sh"))
            self.assertEqual(options.session.headers["Authorization"], "Bearer ring")

    @unittest.mock.patch.dict(service.Options.creds, {
        "default": {
            "url": "arcade",
            "verify": True
        }
    })
    def test_retrieve(self):

        # basic

        options = service.Options({})

        options.session = unittest.mock.MagicMock()

        options.session.request.return_value.json.return_value = [1, 2, 3]

        extra = {}

        options.retrieve(extra)

        self.assertEqual(extra, {
            "options": [1, 2, 3]
        })

        options.session.request.assert_called_once_with(
            "GET",
            "arcade",
            verify=True,
            params={},
            json={}
        )

        # lookups

        data = {
            "path": "disco",
            "params": {"a": 1},
            "body": {"b": 2},
            "results": "numbers",
            "option": "id",
            "title": "name"
        }

        options = service.Options(data)

        options.session = unittest.mock.MagicMock()

        options.session.request.return_value.json.return_value = {
            "numbers": [
                {
                    "id": 1,
                    "name": "one"
                },
                {
                    "id": 2,
                    "name": "two"
                },
                {
                    "id": 3,
                    "name": "three"
                }
            ]
        }

        extra = {}

        options.retrieve(extra)

        self.assertEqual(extra, {
            "options": [1, 2, 3],
            "titles": {
                1: "one",
                2: "two",
                3: "three"
            }
        })

        options.session.request.assert_called_with(
            "GET",
            "arcade/disco",
            verify=True,
            params={"a": 1},
            json={"b": 2}
        )

        # overscore

        data = {
            "path": "disco",
            "params": {"a": 1},
            "body": {"b": 2},
            "results": "big__numbers",
            "option": "id__number",
            "title": "name__string"
        }

        options = service.Options(data)

        options.session = unittest.mock.MagicMock()

        options.session.request.return_value.json.return_value = {
            "big": {
                "numbers": [
                    {
                        "id": {
                            "number": 1
                        },
                        "name": {
                            "string": "one"
                        }
                    },
                    {
                        "id": {
                            "number": 2
                        },
                        "name": {
                            "string": "two"
                        }
                    },
                    {
                        "id": {
                            "number": 3
                        },
                        "name": {
                            "string": "three"
                        }
                    }
                ]
            }
        }

        extra = {}

        options.retrieve(extra)

        self.assertEqual(extra, {
            "options": [1, 2, 3],
            "titles": {
                1: "one",
                2: "two",
                3: "three"
            }
        })

        options.session.request.assert_called_with(
            "GET",
            "arcade/disco",
            verify=True,
            params={"a": 1},
            json={"b": 2}
        )

class TestRestful(unittest.TestCase):

    maxDiff = None

    @unittest.mock.patch("redis.Redis", MockRedis)
    def setUp(self):

        self.app = service.build()
        self.api = self.app.test_client()

    def assertFields(self, fields, data, **kwargs):
        """
        Asserts fields object in list form equals data
        """

        items = fields.to_list()

        self.assertEqual(len(items), len(data), "fields")

        for index, field in enumerate(items):
            self.assertEqual(field, data[index], index)

        for key in kwargs:
            self.assertEqual(getattr(fields, key), kwargs[key], key)

    def assertStatusValue(self, response, code, key, value):
        """
        Assert a response's code and keyed json value are equal.
        Good with checking API responses in full with an outout
        of the json if unequal
        """

        self.assertEqual(response.status_code, code, response.json)
        self.assertEqual(response.json[key], value)

    def assertStatusFields(self, response, code, fields, errors=None, **kwargs):
        """
        Assert a response's code and keyed json fields are equal.
        Good with checking API responses  of options with an outout
        of the json if unequal
        """

        self.assertEqual(response.status_code, code, response.json)

        self.assertEqual(len(fields), len(response.json['fields']), "fields")

        for index, field in enumerate(fields):
            self.assertEqual(field, response.json['fields'][index], index)

        if errors or response.json.get("errors", []) != []:

            self.assertIsNotNone(errors, response.json)
            self.assertIn("errors", response.json, response.json)

            self.assertEqual(errors, response.json['errors'], "errors")

        for key in kwargs:
            self.assertEqual(response.json.get(key), kwargs[key], key)


class TestAPI(TestRestful):

    @unittest.mock.patch.dict(service.Options.creds, {})
    @unittest.mock.patch("redis.Redis", MockRedis)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch('service.open', create=True)
    def test_build(self, mock_open, mock_glob):

        mock_glob.return_value = ["what/options_people.json"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='{"stuff": "things"}').return_value
        ]

        app = service.build()

        self.assertEqual(app.name, "cnc-forge-api")
        self.assertEqual(app.redis.host, "redis.cnc-forge")
        self.assertEqual(app.redis.charset, "utf-8")
        self.assertTrue(app.redis.decode_responses)
        self.assertEqual(service.Options.creds, {
            "people": {
                "stuff": "things",
                "verify": True
            }
        })

class TestHealth(TestRestful):

    def test_get(self):

        self.assertStatusValue(self.api.get("/health"), 200, "message", "OK")


class TestForge(TestRestful):

    @unittest.mock.patch('service.glob.glob')
    @unittest.mock.patch('service.open', create=True)
    def test_forges(self, mock_open, mock_glob):

        mock_glob.return_value = [
            "/opt/service/forge/there.yaml",
            "/opt/service/forge/here.yaml",
            "/opt/service/forge/fields.yaml",
            "/opt/service/forge/values.yaml"
        ]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='description: Here').return_value,
            unittest.mock.mock_open(read_data='description: There').return_value
        ]

        self.assertEqual(service.Forge.forges(), {
            "here": "Here",
            "there": "There"
        })

        mock_glob.assert_called_with("/opt/service/forge/*.yaml")

        mock_open.assert_has_calls([
            unittest.mock.call("/opt/service/forge/here.yaml", "r"),
            unittest.mock.call("/opt/service/forge/there.yaml", "r")
        ])

    @unittest.mock.patch('service.open', create=True)
    def test_forge(self, mock_open):

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='description: Here').return_value
        ]

        self.assertEqual(service.Forge.forge("here"), {
            "id": "here",
            "description": "Here"
        })

        mock_open.assert_has_calls([
            unittest.mock.call("/opt/service/forge/here.yaml", "r")
        ])

    @unittest.mock.patch('service.glob.glob')
    @unittest.mock.patch('service.open', create=True)
    def test_list(self, mock_open, mock_glob):

        mock_glob.return_value = [
            "/opt/service/forge/there.yaml",
            "/opt/service/forge/here.yaml"
        ]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='description: Here').return_value,
            unittest.mock.mock_open(read_data='description: There').return_value,
            unittest.mock.mock_open(read_data='description: Here').return_value
        ]

        self.assertEqual(service.Forge.list(), {
            "forges": [
                {
                    "id": "here",
                    "description": "Here"
                },
                {
                    "id": "there",
                    "description": "There"
                }
            ]
        })

    @unittest.mock.patch('service.glob.glob')
    @unittest.mock.patch('service.open', create=True)
    def test_retrieve(self, mock_open, mock_glob):

        mock_glob.return_value = [
            "/opt/service/forge/here.yaml"
        ]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='description: Here').return_value,
            unittest.mock.mock_open(read_data='description: Here').return_value,
            unittest.mock.mock_open(read_data='description: Here').return_value
        ]

        self.assertEqual(service.Forge.retrieve("here"), {
            "forge": {
                "id": "here",
                "description": "Here"
            },
            "yaml": "description: Here\nid: here\n"
        })

        self.assertEqual(service.Forge.retrieve("there"), ({
            "message": "forge 'there' not found"
        }, 404))

    @unittest.mock.patch('service.glob.glob')
    @unittest.mock.patch('service.open', create=True)
    def test_get(self, mock_open, mock_glob):

        mock_glob.return_value = [
            "/opt/service/forge/there.yaml",
            "/opt/service/forge/here.yaml"
        ]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='description: Here').return_value,
            unittest.mock.mock_open(read_data='description: There').return_value,
            unittest.mock.mock_open(read_data='description: Here').return_value,
            unittest.mock.mock_open(read_data='description: There').return_value,
            unittest.mock.mock_open(read_data='description: Here').return_value
        ]

        self.assertStatusValue(self.api.get("/forge"), 200, "forges", [
            {
                "id": "here",
                "description": "Here"
            },
            {
                "id": "there",
                "description": "There"
            }
        ])

        response = self.api.get("/forge/here")

        self.assertStatusValue(response, 200, "forge", {
            "id": "here",
            "description": "Here"
        })

        self.assertStatusValue(response, 200, "yaml", "description: Here\nid: here\n")


class TestCnC(TestRestful):

    def test___init__(self):

        cnc = service.CnC()

        self.assertIn("port", cnc.env.globals)

    def test_port(self):

        self.assertEqual(service.CnC.port("a-b"), 6566)
        self.assertEqual(service.CnC.port("ac"), 6567)

    def test_values(self):

        cnc = service.CnC()

        fields = opengui.Fields(fields=[
            {"name": "none"},
            {"name": "some", "default": "fun"}
        ])

        self.assertEqual(cnc.values(fields), {
            "none": None,
            "some": "fun"
        })

    def test_ready(self):

        cnc = service.CnC()

        fields = opengui.Fields()

        # missing

        field = {
            "name": "moar",
            "requires": "some"
        }

        self.assertFalse(cnc.ready(fields, field))

        # invalid

        fields.append({
            "name": "some",
            "required": True
        })

        self.assertFalse(cnc.ready(fields, field))

        # requirement met

        fields["some"].value = "fun"

        self.assertTrue(cnc.ready(fields, field))

    def test_satisfied(self):

        cnc = service.CnC()

        # unsatisfied

        field = {
            "name": "happy",
            "condition": "False"
        }

        self.assertFalse(cnc.satisfied(field))

        field = {
            "name": "happy",
            "condition": False,
        }

        self.assertFalse(cnc.satisfied(field))

        # satisfied

        field = {
            "name": "happy",
            "condition": "True"
        }

        self.assertTrue(cnc.satisfied(field))

        field = {
            "name": "happy",
            "condition": True,
        }

        self.assertTrue(cnc.satisfied(field))

    def test_render(self):

        cnc = service.CnC()

        self.assertEqual(cnc.render(
            {
                "{{ people }}": [
                    "{{ stuff }}",
                    True,
                    "{? 1 == 0 ?}",
                    "{? 1 == 1 ?}"
                ],
                "thingies": "{[ things ]}"
            },
            {
                "people": "stuff",
                "stuff": "things",
                "things": [1, 2, 3]
            }
        ), {
            "stuff": [
                "things",
                True,
                False,
                True
            ],
            "thingies": [1, 2, 3]
        })

    @unittest.mock.patch.dict(service.Options.creds, {
        "default": {
            "url": "arcade",
            "verify": True
        }
    })
    @unittest.mock.patch('requests.Session.request')
    def test_field(self, mock_request):

        cnc = service.CnC()

        fields = opengui.Fields(values={"moar": "lees"})

        # clear

        field = {
            "name": "moar",
            "requires": "some"
        }

        cnc.field(fields, field)

        self.assertEqual(len(fields), 0)

        field = {
            "name": "moar",
            "condition": False
        }

        cnc.field(fields, field)

        self.assertEqual(len(fields), 0)

        # default

        fields.append({
            "name": "some",
            "required": True,
            "value": "fun"
        })

        field = {
            "name": "happy",
            "default": "{{ port(some) }} bone",
            "requires": "some"
        }

        cnc.field(fields, field)

        self.assertEqual(len(fields), 2)
        self.assertEqual(fields["happy"].default, "7085 bone")

        # update

        field = {
            "name": "happy",
            "options": [1, 2, 3],
            "requires": "some"
        }

        cnc.field(fields, field)

        self.assertEqual(len(fields), 2)
        self.assertEqual(fields["happy"].default, "7085 bone")
        self.assertEqual(fields["happy"].options, [1, 2, 3])

        # options

        mock_request.return_value.json.return_value = {
            "numbers": [
                {
                    "id": 1,
                    "name": "one"
                },
                {
                    "id": 2,
                    "name": "two"
                },
                {
                    "id": 3,
                    "name": "three"
                }
            ]
        }

        field = {
            "name": "friend",
            "options": {
                "results": "numbers",
                "option": "id",
                "title": "name"
            }
        }

        cnc.field(fields, field)

        self.assertEqual(len(fields), 3)
        self.assertEqual(fields["friend"].options, [1, 2, 3])
        self.assertEqual(fields["friend"].content['titles'], {
            1: "one",
            2: "two",
            3: "three"
        })

    @unittest.mock.patch('service.os.path.exists')
    @unittest.mock.patch('service.open', create=True)
    def test_fields(self, mock_open, mock_exists):

        mock_exists.return_value = True

        mock_open.side_effect = [
           unittest.mock.mock_open(read_data='fields:\n- name: extra').return_value,
           unittest.mock.mock_open(read_data='{}').return_value,
           unittest.mock.mock_open(read_data='{}').return_value,
           unittest.mock.mock_open(read_data='{}').return_value
         ]

        cnc = service.CnC()

        # blank

        forge = {
            "id": "here",
            "description": "Here"
        }

        fields = cnc.fields(forge, {})

        self.assertFields(fields, [
            {
                "name": "forge",
                "description": "what to craft from",
                "readonly": True,
                "value": "here"
            },
            {
                "name": "craft",
                "description": "name of what to craft, used for repos, branches, change requests",
                "validation": '^[a-z][a-z0-9\-]{1,46}$',
                "required": True,
                "trigger": True
            },
            {
                "name": "extra"
            }
        ],ready=True)

        mock_exists.assert_called_once_with("/opt/service/forge/fields.yaml")

        # additional

        forge = {
            "id": "here",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            }
        }

        fields = cnc.fields(forge, {"craft": "fun", "some": "thing"})

        self.assertFields(fields, [
            {
                "name": "forge",
                "description": "what to craft from",
                "readonly": True,
                "value": "here"
            },
            {
                "name": "craft",
                "description": "name of what to craft, used for repos, branches, change requests",
                "validation": '^[a-z][a-z0-9\-]{1,46}$',
                "required": True,
                "trigger": True,
                "value": "fun"
            },
            {
                "name":"some",
                "value":"thing"
            }
        ])

        # override

        forge = {
            "id": "here",
            "description": "Here",
            "input": {
                "craft": "some",
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            }
        }

        fields = cnc.fields(forge, {"some": "thing"})

        self.assertFields(fields, [
            {
                "name": "forge",
                "description": "what to craft from",
                "readonly": True,
                "value": "here"
            },
            {
                "name":"some",
                "value":"thing"
            }
        ])

        # reserved

        forge = {
            "id": "here",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "code"
                    }
                ]
            }
        }

        self.assertRaisesRegex(Exception, "field name 'code' is reserved", cnc.fields, forge, {})

    @unittest.mock.patch("service.Forge.forge")
    @unittest.mock.patch("service.Forge.forges")
    def test_options(self, mock_forges, mock_forge):

        mock_forges.return_value = {}

        self.assertStatusValue(self.api.options("/cnc/nope"), 404, "message", "forge 'nope' not found")

        mock_forges.return_value = {"here": True}

        mock_forge.return_value = {
            "id": "here",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            }
        }

        response = self.api.options("/cnc/here", json={
            "values": {
                "craft": "funtime",
                "some": "thing"
            }
        })

        self.assertStatusFields(response, 200, [
            {
                "name": "forge",
                "description": "what to craft from",
                "readonly": True,
                "value": "here"
            },
            {
                "name": "craft",
                "description": "name of what to craft, used for repos, branches, change requests",
                "validation": '^[a-z][a-z0-9\-]{1,46}$',
                "required": True,
                "trigger": True,
                "value": "funtime"
            },
            {
                "name":"some",
                "value":"thing"
            }
        ], ready=True, valid=True)

    @freezegun.freeze_time("2020-11-02") # 1604275200
    @unittest.mock.patch("service.Forge.forge")
    @unittest.mock.patch("service.Forge.forges")
    @unittest.mock.patch('service.os.path.exists')
    @unittest.mock.patch('service.open', create=True)
    def test_post(self, mock_open, mock_exists, mock_forges, mock_forge):

        def exists(path):

            return path == "/opt/service/forge/values.yaml"

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='values:\n  good: times').return_value,
            unittest.mock.mock_open(read_data='{}').return_value
        ]

        mock_exists.side_effect = exists

        mock_forges.return_value = {}

        # not found

        self.assertStatusValue(self.api.post("/cnc/nope"), 404, "message", "forge 'nope' not found")

        # no action

        mock_forges.return_value = {"here": True}

        mock_forge.return_value = {
            "id": "here",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            }
        }

        self.assertStatusValue(self.api.post("/cnc/here", json={}), 400, "message", "missing action")

        # invalid

        response = self.api.post("/cnc/here", json={
            "values": {
                "craft": "0fun",
                "some": "thing"
            },
            "action": "commit"
        })

        self.assertStatusFields(response, 400, [
            {
                "name": "forge",
                "description": "what to craft from",
                "readonly": True,
                "value": "here"
            },
            {
                "name": "craft",
                "description": "name of what to craft, used for repos, branches, change requests",
                "validation": '^[a-z][a-z0-9\-]{1,46}$',
                "required": True,
                "trigger": True,
                "value": "0fun",
                "errors": ["must match '^[a-z][a-z0-9\\-]{1,46}$'"]
            },
            {
                "name":"some",
                "value":"thing"
            }
        ], ready=True, valid=False)

        # correct

        response = self.api.post("/cnc/here", json={
            "values": {
                "craft": "fun-time",
                "some": "thing"
            },
            "action": "commit"
        })

        self.assertStatusValue(response, 202, "cnc", {
            "id": "fun-time-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "fun-time",
                "code": "fun_time",
                "some": "thing",
                "good": "times",
                "cnc": "fun-time-here-1604275200"
            },
            "status": "Created",
            "action": "commit"
        })

        self.assertEqual(json.loads(self.app.redis.data["/cnc/fun-time-here-1604275200"]), {
            "id": "fun-time-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "fun-time",
                "code": "fun_time",
                "some": "thing",
                "good": "times",
                "cnc": "fun-time-here-1604275200"
            },
            "status": "Created",
            "action": "commit"
        })

        self.assertEqual(self.app.redis.expires["/cnc/fun-time-here-1604275200"], 86400)

        # override multi

        mock_forge.return_value = {
            "id": "here",
            "description": "Here",
            "input": {
                "craft": "many",
                "fields": [
                    {
                        "name": "many"
                    },
                    {
                        "name": "some"
                    }
                ]
            }
        }

        mock_exists.return_value = False

        response = self.api.post("/cnc/here", json={
            "values": {
                "many": ["fun-time"],
                "some": "thing"
            },
            "action": "test"
        })

        self.assertStatusValue(response, 202, "cnc", {
            "id": "fun-time-here-1604275200",
            "description": "Here",
            "input": {
                "craft": "many",
                "fields": [
                    {
                        "name": "many",
                    },
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "many": ["fun-time"],
                "code": "fun_time",
                "some": "thing",
                "cnc": "fun-time-here-1604275200"
            },
            "status": "Created",
            "action": "test"
        })

    def test_list(self):

        class TestList(flask_restful.Resource):

            def get(self):

                return service.CnC.list()

        self.app.api.add_resource(TestList, '/test-list')

        self.app.redis.data["/cnc/funtime-here-1604275200"] = json.dumps({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created"
        })

        self.assertStatusValue(self.api.get("/test-list"), 200, "cncs", [
            {"id": "funtime-here-1604275200"}
        ])

    def test_retrieve(self):

        class TestRetrieve(flask_restful.Resource):

            def get(self, id):

                return service.CnC.retrieve(id)

        self.app.api.add_resource(TestRetrieve, '/test-retrieve/<id>')

        self.app.redis.data["/cnc/funtime-here-1604275200"] = json.dumps({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created"
        })

        self.assertStatusValue(self.api.get("/test-retrieve/nope"), 404, "message", "cnc 'nope' not found")

        response = self.api.get("/test-retrieve/funtime-here-1604275200")

        self.assertStatusValue(response, 200, "cnc", {
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created"
        })

        self.assertStatusValue(response, 200, "yaml", yaml.safe_dump({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created"
        }))

    def test_get(self):

        self.app.redis.data["/cnc/funtime-here-1604275200"] = json.dumps({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created"
        })

        self.assertStatusValue(self.api.get("/cnc"), 200, "cncs", [
            {"id": "funtime-here-1604275200"}
        ])

        self.assertStatusValue(self.api.get("/cnc/funtime-here-1604275200"), 200, "cnc", {
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created"
        })

    def test_patch(self):

        self.app.redis.data["/cnc/funtime-here-1604275200"] = json.dumps({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created",
            "traceback": "scroll",
            "content": "monetized"
        })

        response = self.api.patch("/cnc/funtime-here-1604275200")

        self.assertStatusValue(response, 201, "cnc", {
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Retry"
        })

        self.assertStatusValue(response, 201, "yaml", yaml.safe_dump({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Retry"
        }))

        self.assertStatusValue(self.api.patch("/cnc/nope"), 404, "message", "cnc 'nope' not found")


    def test_delete(self):

        self.app.redis.data["/cnc/funtime-here-1604275200"] = json.dumps({
            "id": "funtime-here-1604275200",
            "description": "Here",
            "input": {
                "fields": [
                    {
                        "name": "some"
                    }
                ]
            },
            "values": {
                "forge": "here",
                "craft": "funtime",
                "some": "thing"
            },
            "status": "Created",
            "traceback": "scroll",
            "content": "monetized"
        })

        response = self.api.delete("/cnc/funtime-here-1604275200")

        self.assertStatusValue(response, 201, "deleted", 1)

        self.assertEqual(self.app.redis.data, {})

        self.assertStatusValue(self.api.delete("/cnc/nope"), 404, "message", "cnc 'nope' not found")
