import unittest
import unittest.mock

import cnc
import jinja2

class TestService(unittest.TestCase):

    def setUp(self):

        daemon = unittest.mock.MagicMock()

        daemon.env = jinja2.Environment()

        self.cnc = cnc.CnC(daemon)

    def test_transform(self):

        self.assertEqual('1', self.cnc.transform("{{ a }}", {"a": 1}))
        self.assertEqual(['1'], self.cnc.transform(["{{ a }}"], {"a": 1}))
        self.assertEqual({"b": '1'}, self.cnc.transform({"b": "{{ a }}"}, {"a": 1}))
        self.assertEqual('True', self.cnc.transform("{{ a == 1 }}", {"a": 1}))
        self.assertEqual('False', self.cnc.transform("{{ a != 1 }}", {"a": 1}))


    def test_transpose(self):

        self.assertEqual({"b": 1}, self.cnc.transpose({"transpose": {"b": "a"}}, {"a": 1}))

    def test_iterate(self):

        values = {
            "a": 1,
            "cs": [2, 3],
            "ds": "nuts"
        }

        self.assertEqual(self.cnc.iterate({}, values), [{}])

        block = {
            "transpose": {
                "b": "a"
            },
            "iterate": {
                "c": "cs",
                "d": "ds"
            }
        }

        self.assertEqual(self.cnc.iterate(block, values), [
            {"b": 1, "c": 2, "d": "n"},
            {"b": 1, "c": 2, "d": "u"},
            {"b": 1, "c": 2, "d": "t"},
            {"b": 1, "c": 2, "d": "s"},
            {"b": 1, "c": 3, "d": "n"},
            {"b": 1, "c": 3, "d": "u"},
            {"b": 1, "c": 3, "d": "t"},
            {"b": 1, "c": 3, "d": "s"}
        ])

    def test_condition(self):

        self.assertTrue(self.cnc.condition({}, {}))

        block = {
            "condition": "{{ a == 1 }}"
        }

        self.assertTrue(self.cnc.condition(block, {"a": 1}))
        self.assertFalse(self.cnc.condition(block, {"a": 2}))

    def test_each(self):

        values = {
            "a": 1,
            "cs": [2, 3],
            "ds": "nuts"
        }

        block = {
            "transpose": {
                "b": "a"
            },
            "iterate": {
                "c": "cs",
                "d": "ds"
            },
            "condition": "{{ c != 3 and d != 't' }}"
        }

        self.assertEqual(list(self.cnc.each([block], values)), [
            (block, {"a": 1, "cs": [2, 3], "ds": "nuts", "b": 1, "c": 2, "d": "n"}),
            (block, {"a": 1, "cs": [2, 3], "ds": "nuts", "b": 1, "c": 2, "d": "u"}),
            (block, {"a": 1, "cs": [2, 3], "ds": "nuts", "b": 1, "c": 2, "d": "s"})
        ])
