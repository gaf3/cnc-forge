import unittest
import unittest.mock

import service


class MockRedis:

    def __init__(self, host):

        self.host = host

        self.data = {}
        self.expires = {}
        self.messages = []

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

class TestRestful(unittest.TestCase):

    @unittest.mock.patch('service.open', create=True)
    @unittest.mock.patch("redis.Redis", MockRedis)
    def setUp(self, mock_open):

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='{"host": "redi.com"}').return_value
        ]

        self.app = service.build()
        self.api = self.app.test_client()

    def assertFields(self, fields, data):
        """
        Asserts fields object in list form equals data
        """

        items = fields.to_list()

        self.assertEqual(len(items), len(data), "fields")

        for index, field in enumerate(items):
            self.assertEqual(field, data[index], index)

    def assertStatusValue(self, response, code, key, value):
        """
        Assert a response's code and keyed json value are equal.
        Good with checking API responses in full with an outout
        of the json if unequal
        """

        self.assertEqual(response.status_code, code, response.json)
        self.assertEqual(response.json[key], value)

    def assertStatusFields(self, response, code, fields, errors=None):
        """
        Assert a response's code and keyed json fields are equal.
        Good with checking API responses  of options with an outout
        of the json if unequal
        """

        self.assertEqual(response.status_code, code, response.json)

        self.assertEqual(len(fields), len(response.json['fields']), "fields")

        for index, field in enumerate(fields):
            self.assertEqual(field, response.json['fields'][index], index)

        if errors or "errors" in response.json:

            self.assertIsNotNone(errors, response.json)
            self.assertIn("errors", response.json, response.json)

            self.assertEqual(errors, response.json['errors'], "errors")


class TestAPI(TestRestful):

    @unittest.mock.patch('service.open', create=True)
    @unittest.mock.patch("redis.Redis", MockRedis)
    def test_build(self, mock_open):

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='{"host": "redi.com"}').return_value
        ]

        app = service.build()

        self.assertEqual(app.name, "cnc-forge-api")

        mock_open.assert_has_calls([
            unittest.mock.call("/opt/service/secret/redis.json", "r")
        ])

class TestHealth(TestRestful):

    def test_get(self):

        self.assertStatusValue(self.api.get("/health"), 200, "message", "OK")
