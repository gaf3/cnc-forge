import unittest
import unittest.mock

import requests.auth

import service


class TestRestful(unittest.TestCase):

    maxDiff = None

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

    def test_build(self):

        app = service.build()

        self.assertEqual(app.name, "cnc-forge-options")


class TestHealth(TestRestful):

    def test_get(self):

        self.assertStatusValue(self.api.get("/health"), 200, "message", "OK")


class TestSimple(TestRestful):

    def test_get(self):

        self.assertEqual(self.api.get("/simple").json, ["people", "stuff", "things"])


class TestComplex(TestRestful):

    def test_get(self):

        self.assertStatusValue(self.api.get("/complex"), 200, "fruits", [
            {
                "id": 1,
                "name": "apple",
                "meta": {
                    "fancy": "Apple"
                }
            },
            {
                "id": 2,
                "name": "pear",
                "meta": {
                    "fancy": "Pear"
                }
            },
            {
                "id": 3,
                "name": "orange",
                "meta": {
                    "fancy": "Orange"
                }
            }
        ])


class TestBasic(TestRestful):

    def test_get(self):

        self.assertStatusValue(self.api.get("/basic"), 401, "message", "Unauthorized")

        headers = {
            "Authorization": requests.auth._basic_auth_str("my", "self")
        }

        self.assertEqual(self.api.get("/basic", headers=headers).json, ["bass", "how", "low"])


class TestToken(TestRestful):

    def test_get(self):

        self.assertStatusValue(self.api.get("/token"), 401, "message", "Unauthorized")

        headers = {
            "Authorization": "Bearer funspot"
        }

        self.assertEqual(self.api.get("/token", headers=headers).json, ["galaga", "pacman", "defender"])
