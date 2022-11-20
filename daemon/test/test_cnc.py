import unittest
import unittest.mock

import json
import yaml

import cnc
import jinja2

class TestCnC(unittest.TestCase):

    def setUp(self):

        self.cnc = cnc.CnC({"id": "sweat"})

    def test___init__(self):

        init = cnc.CnC({})
        self.assertEqual(init.data, {})
        self.assertTrue(init.engine.env.keep_trailing_newline)

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

        self.assertEqual(self.cnc.source({"source": {"value": "yep"}}), "yep")

        self.assertRaisesRegex(Exception, "invalid path: ..", self.cnc.source, {"source": ".."})

        self.assertEqual(self.cnc.source({"source": "stuff"}, path=True), "/opt/service/cnc/sweat/source/stuff")

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='src').return_value
        ]

        self.assertEqual(self.cnc.source({"source": "stuff"}), "src")

        mock_open.assert_called_once_with("/opt/service/cnc/sweat/source/stuff", "r")

    @unittest.mock.patch("cnc.open", create=True)
    @unittest.mock.patch("os.path.exists")
    def test_destination(self, mock_exists, mock_open):

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

        mock_open.reset_mock()
        mock_exists.return_value = False
        mock_open.side_effect = [mock_read, mock_write]

        self.cnc.destination({"destination": "things", "replace": False}, "dest")

        mock_open.assert_called_with("/opt/service/cnc/sweat/destination/things", "w")
        mock_write.write.assert_called_once_with("dest")

        mock_open.reset_mock()
        mock_exists.return_value = True

        self.cnc.destination({"destination": "things", "replace": False}, "dest")

        mock_open.assert_not_called()

    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("shutil.copy")
    def test_copy(self, mock_copy, mock_exists):

        # no replace

        mock_exists.return_value = True

        self.cnc.copy({"source": "src", "destination": "dest", "replace": False})

        mock_copy.assert_not_called()

        self.cnc.copy({"source": "src", "destination": "dest"})

        mock_copy.assert_called_once_with(
            "/opt/service/cnc/sweat/source/src",
            "/opt/service/cnc/sweat/destination/dest"
        )

    @unittest.mock.patch("os.path.isdir")
    @unittest.mock.patch("shutil.rmtree")
    @unittest.mock.patch("os.remove")
    def test_remove(self, mock_remove, mock_rmtree, mock_isdir):

        # dir

        mock_isdir.return_value = True

        self.cnc.remove({"destination": "dest"})

        mock_rmtree.assert_called_once_with(
            "/opt/service/cnc/sweat/destination/dest"
        )

        # file

        mock_isdir.return_value = False

        self.cnc.remove({"destination": "dest"})

        mock_remove.assert_called_once_with(
            "/opt/service/cnc/sweat/destination/dest"
        )

    def test_text(self):

        destination = "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n"

        # add

        self.assertEqual(self.cnc.text("nope\n", destination, False, False), "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n")
        self.assertEqual(self.cnc.text("foe\n", destination, True, False), "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n")
        self.assertEqual(self.cnc.text("yep\n", destination, True, False), "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\nyep\n")
        self.assertEqual(self.cnc.text("yep\n", destination, "here", False), "fee\nfie\nyep\n  # cnc-forge: here  \nfoe\nfum\n")

        # remove

        self.assertEqual(self.cnc.text("nope\n", "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n", False, True), destination)
        self.assertEqual(self.cnc.text("foe\n", "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n", True, True), "fee\nfie\n  # cnc-forge: here  \nfum\n")
        self.assertEqual(self.cnc.text("yep\n", "fee\nfie\n  # cnc-forge: here  \nfoe\nfum\nyep\n", True, True), destination)
        self.assertEqual(self.cnc.text("yep", "fee\nfie\nyep\n  # cnc-forge: here  \nfoe\nfum\n", "here", True), destination)

    def test_json(self):

        # add

        destination = json.dumps({
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        })
        source = json.dumps({"g": "h"})

        self.assertEqual(json.loads(self.cnc.json(source, destination, "a__b", False)), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"},
                    {"g": "h"}
                ]
            }
        })

        # remove

        destination = json.dumps({
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"},
                    {"g": "h"}
                ]
            }
        })
        source = json.dumps({"g": "h"})

        self.assertEqual(json.loads(self.cnc.json(source, destination, "a__b", True)), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        })

    def test_yaml(self):

        # add

        destination = yaml.safe_dump({
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
                ]
            }
        })
        source = yaml.safe_dump({"g": "h"})

        self.assertEqual(yaml.safe_load(self.cnc.yaml(source, destination, "a__b", False)), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"},
                    {"g": "h"}
                ]
            }
        })

        # remove

        destination = yaml.safe_dump({
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"},
                    {"g": "h"}
                ]
            }
        })
        source = yaml.safe_dump({"g": "h"})

        self.assertEqual(yaml.safe_load(self.cnc.yaml(source, destination, "a__b", True)), {
            "a": {
                "b": [
                    {"c": "d"},
                    {"e": "f"}
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
    @unittest.mock.patch("os.path.isdir")
    @unittest.mock.patch("os.remove")
    def test_file(self, mock_remove, mock_isdir, mock_stat, mock_mode, mock_open, mock_copy):

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

        # Remove

        mock_isdir.return_value = False

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "remove": ["a/b/c"],
            "transform": []
        }

        self.cnc.file(content, None)

        mock_remove.assert_called_once_with(
            "/opt/service/cnc/sweat/destination/a/b/c"
        )

        # Text

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data="{{ sure }}\n").return_value,
            unittest.mock.mock_open(read_data="fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n").return_value,
            mock_write
        ]

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": [],
            "text": "{{ there }}"
        }

        self.cnc.file(content, {"sure": "yep", "there": "here"})

        mock_write.write.assert_called_once_with("fee\nfie\nyep\n  # cnc-forge: here  \nfoe\nfum\n")

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data="{{ sure }}\n").return_value,
            unittest.mock.mock_open(read_data="fee\nfie\n  # cnc-forge: here  \nfoe\nfum\n").return_value,
            mock_write
        ]

        content = {
            "source": "a/b/c",
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": [],
            "text": True
        }

        self.cnc.file(content, {"sure": "yep", "there": "here"})

        mock_write.write.assert_called_once_with("fee\nfie\n  # cnc-forge: here  \nfoe\nfum\nyep\n")

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
            "json": "{{ there }}"
        }

        self.cnc.file(content, {"sure": "yep", "there": "here"})

        mock_write.write.assert_called_once_with('{\n    "here": [\n        "yep"\n    ]\n}\n')

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
            "yaml": "{{ there }}"
        }

        self.cnc.file(content, {"sure": "yep", "there": "here"})

        mock_write.write.assert_called_once_with('here:\n- yep\n')

        # Value

        mock_write = unittest.mock.mock_open().return_value

        mock_open.side_effect = [
            mock_write
        ]

        mock_stat.return_value.st_mode = "ala"

        content = {
            "source": {
                "value": "hey"
            },
            "destination": "a/b/c",
            "include": [],
            "exclude": [],
            "preserve": [],
            "transform": []
        }

        self.cnc.file(content, {"sure": "yep"})

        mock_write.write.assert_called_once_with('hey')

        mock_stat.assert_not_called()

        mock_mode.assert_not_called()

        # Mode

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

    @unittest.mock.patch("os.path.isdir")
    @unittest.mock.patch("glob.glob")
    def test_content(self, mock_glob, mock_isdir):

        self.cnc.craft = unittest.mock.MagicMock()

        mock_glob.return_value = ["/opt/service/cnc/sweat/destination/a/b/c"]
        mock_isdir.return_value = False

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

        # Glob

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

        # Dir

        mock_isdir.return_value = True

        content = {
            "source": "{{ start }}/"
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

        mock_isdir.return_value = False

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

        # dict soure

        content = {
            "source": {
                "value": "template"
            },
            "destination": "{{ start }}/d",
            "include": ["i"],
            "exclude": ["j"],
            "preserve": ["k"],
            "transform": ["l"]
        }

        self.cnc.content(content, {"start": "a/b"})

        self.cnc.craft.assert_called_with({
            "source": {
                "value": "template"
            },
            "destination": "a/b/d",
            "include": ["i"],
            "exclude": ["j"],
            "preserve": ["k"],
            "transform": ["l"]
        }, {"start": "a/b"})

    @unittest.mock.patch("github.GitHub")
    def test_change(self, mock_github):

        self.cnc.content = unittest.mock.MagicMock()

        # commit

        change = {
            "github": {
                "repo": "{{ here }}"
            },
            "content": [
                {"condition": "{{ here == 'there' }}"},
                {"condition": "{{ here == 'here' }}"}
            ],
            "remove": False
        }

        self.cnc.change(change, {"here": "there"})

        mock_github.return_value.change.assert_called_once_with()

        self.cnc.content.assert_called_once_with(
            {"remove": False},
            {"here": "there"}
        )

        # remove

        change = {
            "github": {
                "repo": "{{ here }}"
            },
            "content": [
                {"condition": "{{ here == 'there' }}", "remove": True},
                {"condition": "{{ here == 'here' }}"}
            ],
            "remove": False
        }

        self.cnc.change(change, {"here": "there"})

        self.cnc.content.assert_called_with(
            {"remove": True},
            {"here": "there"}
        )

    @unittest.mock.patch("github.GitHub")
    def test_code(self, mock_github):

        self.cnc.change = unittest.mock.MagicMock()

        # commit

        code = {
            "github": {
                "repo": "{{ here }}"
            },
            "change": [
                {"condition": "{{ here == 'there' }}"},
                {"condition": "{{ here == 'here' }}"}
            ],
            "remove": False
        }

        self.cnc.code(code, {"here": "there"})

        mock_github.return_value.code.assert_called_once_with()

        self.cnc.change.assert_called_once_with(
            {"remove": False},
            {"here": "there"}
        )

        mock_github.return_value.commit.assert_called_once_with()

        # remove

        code = {
            "github": {
                "repo": "{{ here }}"
            },
            "change": [
                {"condition": "{{ here == 'there' }}", "remove": True},
                {"condition": "{{ here == 'here' }}"}
            ],
            "remove": False
        }

        self.cnc.code(code, {"here": "there"})

        self.cnc.change.assert_called_with(
            {"remove": True},
            {"here": "there"}
        )

    def test_link(self):

        self.cnc.link("sure")
        self.cnc.link("sure")
        self.assertEqual(self.cnc.data["links"], ["sure"])

    @unittest.mock.patch("os.makedirs")
    @unittest.mock.patch("shutil.rmtree")
    def test_process(self, mock_rmtree, mock_makedirs):

        self.cnc.code = unittest.mock.MagicMock()

        # test

        self.cnc.data = {
            "id": "sweat",
            "output": {
                "code": [
                    {"condition": "{{ here == 'there' }}"},
                    {"condition": "{{ here == 'here' }}"}
                ]
            },
            "values": {"here": "there"},
            "action": "test"
        }

        self.cnc.process()

        self.assertEqual(self.cnc.data , {
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
            "action": "test"
        })

        mock_makedirs.assert_called_once_with("/opt/service/cnc/sweat")

        self.cnc.code.assert_called_once_with(
            {"remove": False},
            {"here": "there"}
        )

        mock_rmtree.assert_has_calls([
            unittest.mock.call("/opt/service/cnc/sweat", ignore_errors=True),
            unittest.mock.call("/opt/service/cnc/sweat/source", ignore_errors=True)
        ])

        # commit

        self.cnc.data = {
            "id": "sweat",
            "output": {
                "code": [
                    {"condition": "{{ here == 'there' }}"},
                    {"condition": "{{ here == 'here' }}"}
                ]
            },
            "values": {"here": "there"},
            "action": "commit"
        }

        self.cnc.process()

        self.assertEqual(self.cnc.data , {
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
            "action": "commit"
        })

        mock_makedirs.assert_called_with("/opt/service/cnc/sweat")

        self.cnc.code.assert_called_with(
            {"remove": False},
            {"here": "there"}
        )

        # remove

        self.cnc.data = {
            "id": "sweat",
            "output": {
                "code": [
                    {"condition": "{{ here == 'there' }}"},
                    {"condition": "{{ here == 'here' }}"}
                ]
            },
            "values": {"here": "there"},
            "action": "remove"
        }

        self.cnc.process()

        self.assertEqual(self.cnc.data , {
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
            "action": "remove"
        })

        mock_makedirs.assert_called_with("/opt/service/cnc/sweat")

        self.cnc.code.assert_called_with(
            {"remove": True},
            {"here": "there"}
        )
