import unittest
import unittest.mock

import json
import yaml

import cnc
import jinja2

class TestCnC(unittest.TestCase):

    def setUp(self):

        daemon = unittest.mock.MagicMock()
        daemon.env = jinja2.Environment()
        self.cnc = cnc.CnC(daemon)
        self.cnc.data = {"id": "sweat"}

    def test___init__(self):

        daemon = unittest.mock.MagicMock()
        daemon.env = jinja2.Environment()
        self.assertEqual(cnc.CnC(daemon).daemon, daemon)

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

        self.assertEqual(list(self.cnc.each(block, values)), [
            (block, {"a": 1, "cs": [2, 3], "ds": "nuts", "b": 1, "c": 2, "d": "n"}),
            (block, {"a": 1, "cs": [2, 3], "ds": "nuts", "b": 1, "c": 2, "d": "u"}),
            (block, {"a": 1, "cs": [2, 3], "ds": "nuts", "b": 1, "c": 2, "d": "s"})
        ])

    def test_exclude(self):

        self.assertFalse(self.cnc.exclude({"include": ["a"], "exclude": [], "source": "a"}))
        self.assertFalse(self.cnc.exclude({"include": ["a*"], "exclude": [], "source": "ab"}))
        self.assertTrue(self.cnc.exclude({"include": [], "exclude": ["a"], "source": "a"}))
        self.assertTrue(self.cnc.exclude({"include": [], "exclude": ["a*"], "source": "ab"}))
        self.assertFalse(self.cnc.exclude({"include": [], "exclude": [], "source": "a"}))

    def test_preserve(self):

        self.assertFalse(self.cnc.preserve({"transform": ["a"], "preserve": [], "source": "a"}))
        self.assertFalse(self.cnc.preserve({"transform": ["a*"], "preserve": [], "source": "ab"}))
        self.assertTrue(self.cnc.preserve({"transform": [], "preserve": ["a"], "source": "a"}))
        self.assertTrue(self.cnc.preserve({"transform": [], "preserve": ["a*"], "source": "ab"}))
        self.assertFalse(self.cnc.preserve({"transform": [], "preserve": [], "source": "a"}))

    def test_base(self):

        self.assertEqual(self.cnc.base(), "/opt/service/cnc/sweat")

    def test_relative(self):

        self.assertEqual(self.cnc.relative("/opt/service/cnc/sweat/source/a/b/c"), "a/b/c")

    @unittest.mock.patch("cnc.open", create=True)
    def test_source(self, mock_open):

        self.assertRaisesRegex(Exception, "invalid path: ..", self.cnc.source, {"source": ".."})

        self.assertEqual(self.cnc.source({"source": "stuff"}, path=True), "/opt/service/cnc/sweat/source/stuff")

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='src').return_value
        ]

        self.assertEqual(self.cnc.source({"source": "stuff"}), "src")

        mock_open.assert_called_once_with("/opt/service/cnc/sweat/source/stuff", "r")

    @unittest.mock.patch("cnc.open", create=True)
    def test_destination(self, mock_open):

        self.assertRaisesRegex(Exception, "invalid path: ..", self.cnc.destination, {"destination": ".."})

        self.assertEqual(self.cnc.destination({"destination": "things"}, path=True), "/opt/service/cnc/sweat/destination/things")

        mock_read = unittest.mock.mock_open(read_data='dest').return_value
        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [mock_read, mock_write]

        self.assertEqual(self.cnc.destination({"destination": "things"}), "dest")

        mock_open.assert_called_once_with("/opt/service/cnc/sweat/destination/things", "r")

        self.cnc.destination({"destination": "things"}, "dest")

        mock_open.assert_called_with("/opt/service/cnc/sweat/destination/things", "w")
        mock_write.write.assert_called_once_with("dest")

    @unittest.mock.patch("shutil.copy")
    def test_copy(self, mock_copy):

        self.cnc.copy({"source": "src", "destination": "dest"})

        mock_copy.assert_called_once_with(
            "/opt/service/cnc/sweat/source/src",
            "/opt/service/cnc/sweat/destination/dest"
        )

    def test_text(self):

        destination = "fie\nfie\n  # cnc-forge: here  \nfoe\nfum\n"

        self.assertEqual(self.cnc.text("nope\n", destination, False), "fie\nfie\n  # cnc-forge: here  \nfoe\nfum\n")
        self.assertEqual(self.cnc.text("foe\n", destination, True), "fie\nfie\n  # cnc-forge: here  \nfoe\nfum\n")
        self.assertEqual(self.cnc.text("yep\n", destination, True), "fie\nfie\n  # cnc-forge: here  \nfoe\nfum\nyep\n")
        self.assertEqual(self.cnc.text("yep\n", destination, "here"), "fie\nfie\nyep\n  # cnc-forge: here  \nfoe\nfum\n")

    def test_value(self):

        value = {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        }

        self.assertEqual(self.cnc.value(value, False), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        })
        self.assertEqual(self.cnc.value(value, "a"), {
            "b": [
                {"c": "d"},
                {"e": "f"}
            ]
        })
        self.assertEqual(self.cnc.value(value, "a.b"), [
            {"c": "d"},
            {"e": "f"}
        ])
        self.assertEqual(self.cnc.value(value, "a.b.1"), {
            "e": "f"
        })
        self.assertEqual(self.cnc.value(value, "a.b.1.e"), "f")

    def test_json(self):

        destination = json.dumps({
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        })
        source = json.dumps({"g": "h"})

        self.assertEqual(json.loads(self.cnc.json(source, destination, "a.b")), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"},
                    {"g": "h"}
                ]
            }
        })

    def test_yaml(self):

        destination = yaml.safe_dump({
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        })
        source = yaml.safe_dump({"g": "h"})

        self.assertEqual(yaml.safe_load(self.cnc.yaml(source, destination, "a.b")), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"},
                    {"g": "h"}
                ]
            }
        })

    @unittest.mock.patch("os.chmod")
    @unittest.mock.patch("os.stat")
    def test_mode(self, mock_stat, mock_mode):

        mock_stat.return_value.st_mode = "ala"

        self.cnc.mode({"source": "src", "destination": "dest"})

        mock_stat.assert_called_once_with(
            "/opt/service/cnc/sweat/source/src"
        )

        mock_mode.assert_called_once_with(
            "/opt/service/cnc/sweat/destination/dest",
            "ala"
        )

    @unittest.mock.patch("os.listdir")
    def test_directory(self, mock_listdir):

        mock_listdir.return_value = ["c"]

        self.cnc.craft = unittest.mock.MagicMock()

        # .git

        content = {
            "source": "a/b/.git",
            "destination": "a/b/.git",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }

        self.cnc.directory(content, None)

        self.cnc.craft.assert_not_called()

        # root

        content = {
            "source": "",
            "destination": "",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }

        self.cnc.craft(content, None)

        self.cnc.craft.assert_called_once_with({
            "source": "",
            "destination": "",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }, None)

        # regular

        content = {
            "source": "a/b",
            "destination": "a/b",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }

        self.cnc.directory(content, None)

        self.cnc.craft.assert_called_with({
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }, None)

    @unittest.mock.patch("shutil.copy")
    @unittest.mock.patch("cnc.open", create=True)
    @unittest.mock.patch("os.chmod")
    @unittest.mock.patch("os.stat")
    def test_file(self, mock_stat, mock_mode, mock_open, mock_copy):

        # Copy

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": ["a/b/c"],
            "transform": []
        }

        self.cnc.file(content, None)

        mock_copy.assert_called_once_with(
            "/opt/service/cnc/sweat/source/a/b/c",
            "/opt/service/cnc/sweat/destination/a/b/c"
        )

        # Text

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data="{{ sure }}\n").return_value,
            unittest.mock.mock_open(read_data="fie\nfie\n  # cnc-forge: here  \nfoe\nfum\n").return_value,
            mock_write
        ]

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": [],
            "text": "here"
        }

        self.cnc.file(content, {"sure": "yep"})

        mock_write.write.assert_called_once_with("fie\nfie\nyep\n  # cnc-forge: here  \nfoe\nfum\n")

        # JSON

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='"{{ sure }}"').return_value,
            unittest.mock.mock_open(read_data='{"here": []}').return_value,
            mock_write
        ]

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": [],
            "json": "here"
        }

        self.cnc.file(content, {"sure": "yep"})

        mock_write.write.assert_called_once_with('{\n    "here": [\n        "yep"\n    ]\n}')

        # YAML

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='"{{ sure }}"').return_value,
            unittest.mock.mock_open(read_data='here: []').return_value,
            mock_write
        ]

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": [],
            "yaml": "here"
        }

        self.cnc.file(content, {"sure": "yep"})

        mock_write.write.assert_called_once_with('here:\n- yep\n')

        # Transform

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='{{ sure }}').return_value,
            mock_write
        ]

        mock_stat.return_value.st_mode = "ala"

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }

        self.cnc.file(content, {"sure": "yep"})

        mock_write.write.assert_called_once_with('yep')

        mock_stat.assert_called_once_with(
            "/opt/service/cnc/sweat/source/a/b/c"
        )

        mock_mode.assert_called_once_with(
            "/opt/service/cnc/sweat/destination/a/b/c",
            "ala"
        )

    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("os.makedirs")
    @unittest.mock.patch("os.path.isdir")
    @unittest.mock.patch("os.listdir")
    @unittest.mock.patch("shutil.copy")
    def test_craft(self, mock_copy, mock_listdir, mock_isdir, mock_makedirs, mock_exists, mock_print):

        # Excluded

        content = {
            "source": "a",
            "include": [],
            "exclude": ["a"]
        }

        self.cnc.craft(content, None)

        mock_print.assert_not_called()

        # Directory

        mock_exists.return_value = False
        mock_isdir.return_value = True
        mock_listdir.return_value = ["c"]

        content = {
            "source": "a/b",
            "destination": "a/b",
            "include": [],
            "exclude": ["a/b/*"],
            "preserve": [],
            "transform": []
        }

        self.cnc.craft(content, None)

        mock_print.assert_called_once_with(content)

        # Copy

        mock_exists.return_value = True
        mock_isdir.return_value = False

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": ["a/b/c"],
            "transform": []
        }

        self.cnc.craft(content, None)

        mock_copy.assert_called_once_with(
            "/opt/service/cnc/sweat/source/a/b/c",
            "/opt/service/cnc/sweat/destination/a/b/c"
        )

        # Content

        mock_exists.side_effect = Exception("whoops")

        self.assertRaisesRegex(Exception, "whoops", self.cnc.craft, content, {"sure": "yep"})

        self.assertEqual(self.cnc.data["content"], content)

    @unittest.mock.patch("glob.glob")
    def test_content(self, mock_glob):

        self.cnc.craft = unittest.mock.MagicMock()

        mock_glob.return_value = ["/opt/service/cnc/sweat/destination/a/b/c"]

        # Root

        content = {
            "source": "/"
        }

        self.cnc.content(content, {})

        self.cnc.craft.assert_called_once_with({
            "source": "",
            "destination": "",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }, {})

        # Minimal

        content = {
            "source": "{{ start }}/*"
        }

        self.cnc.content(content, {"start": "a/b"})

        self.cnc.craft.assert_called_with({
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }, {"start": "a/b"})

        # Converting

        content = {
            "source": "{{ start }}/c",
            "destination": "{{ start }}/d",
            "include": "e/",
            "exclude": "f",
            "preserve": "g",
            "transform": "h"
        }

        self.cnc.content(content, {"start": "a/b"})

        self.cnc.craft.assert_called_with({
            "source": "a/b/c",
            "destination": "a/b/d",
            "include": ["e"],
            "exclude": ["f"],
            "preserve": ["g"],
            "transform": ["h"]
        }, {"start": "a/b"})

        # As is

        content = {
            "source": "{{ start }}/c",
            "destination": "{{ start }}/d",
            "include": ["i"],
            "exclude": ["j"],
            "preserve": ["k"],
            "transform": ["l"]
        }

        self.cnc.content(content, {"start": "a/b"})

        self.cnc.craft.assert_called_with({
            "source": "a/b/c",
            "destination": "a/b/d",
            "include": ["i"],
            "exclude": ["j"],
            "preserve": ["k"],
            "transform": ["l"]
        }, {"start": "a/b"})

    def test_change(self):

        self.cnc.content = unittest.mock.MagicMock()

        change = {
            "github": {
                "repo": "{{ here }}"
            },
            "content": [
                {"condition": "{{ here == 'there' }}"},
                {"condition": "{{ here == 'here' }}"}
            ]
        }

        self.cnc.change(change, {"here": "there"})

        self.cnc.daemon.github.change.assert_called_once_with(self.cnc, {"repo": "there"})

        self.cnc.content.assert_called_once_with(
            {"condition": "{{ here == 'there' }}"},
            {"here": "there"}
        )

    def test_code(self):

        self.cnc.change = unittest.mock.MagicMock()

        code = {
            "github": {
                "repo": "{{ here }}"
            },
            "change": [
                {"condition": "{{ here == 'there' }}"},
                {"condition": "{{ here == 'here' }}"}
            ]
        }

        self.cnc.code(code, {"here": "there"})

        self.cnc.daemon.github.clone.assert_called_once_with(self.cnc, {"repo": "there"})

        self.cnc.change.assert_called_once_with(
            {"condition": "{{ here == 'there' }}"},
            {"here": "there"}
        )

        self.cnc.daemon.github.commit.assert_called_once_with(self.cnc, {"repo": "there"})

    def test_link(self):

        self.cnc.link("sure")
        self.cnc.link("sure")
        self.assertEqual(self.cnc.data["links"], ["sure"])

    @unittest.mock.patch("os.makedirs")
    @unittest.mock.patch("shutil.rmtree")
    def test_process(self, mock_rmtree, mock_makedirs):

        self.cnc.code = unittest.mock.MagicMock()

        # Testing

        data = {
            "id": "sweat",
            "output": {
                "code": [
                    {"condition": "{{ here == 'there' }}"},
                    {"condition": "{{ here == 'here' }}"}
                ]
            },
            "values": {"here": "there"},
            "test": True
        }

        self.cnc.process(data)

        self.assertEqual(data, {
            "id": "sweat",
            "output": {
                "code": [
                    {"condition": "{{ here == 'there' }}"},
                    {"condition": "{{ here == 'here' }}"}
                ]
            },
            "values": {"here": "there"},
            "code": [
                {"condition": "{{ here == 'there' }}"},
                {"condition": "{{ here == 'here' }}"}
            ],
            "status": "Completed",
            "test": True
        })

        mock_makedirs.assert_called_once_with("/opt/service/cnc/sweat")

        self.cnc.code.assert_called_once_with(
            {"condition": "{{ here == 'there' }}"},
            {"here": "there"}
        )

        mock_rmtree.assert_has_calls([
            unittest.mock.call("/opt/service/cnc/sweat", ignore_errors=True),
            unittest.mock.call("/opt/service/cnc/sweat/source", ignore_errors=True)
        ])

        # Committing

        data = {
            "id": "sweat",
            "output": {
                "code": [
                    {"condition": "{{ here == 'there' }}"},
                    {"condition": "{{ here == 'here' }}"}
                ]
            },
            "values": {"here": "there"},
            "test": False
        }

        self.cnc.process(data)

        mock_rmtree.assert_has_calls([
            unittest.mock.call("/opt/service/cnc/sweat", ignore_errors=True),
            unittest.mock.call("/opt/service/cnc/sweat", ignore_errors=True)
        ])
