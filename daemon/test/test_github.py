import unittest
import unittest.mock

import base64
import requests

import github

class TestGitHub(unittest.TestCase):

    maxDiff = None

    @unittest.mock.patch.dict(github.GitHub.creds, {
        "default": {
            "user": "arcade",
            "token": "fire",
            "host": "most",
            "url":  "curl"
        }
    })
    def setUp(self):

        cnc = unittest.mock.MagicMock()
        cnc.data = {"output": {}}

        self.github = github.GitHub(cnc, {"repo": "git.com"})
        self.github.api = unittest.mock.MagicMock()

    @unittest.mock.patch.dict(github.GitHub.creds, {
        "people": {
            "host": "stuff",
            "user": "things"
        }
    })
    @unittest.mock.patch('github.open', create=True)
    @unittest.mock.patch("github.subprocess.check_output")
    def test_ssh(self, mock_subprocess, mock_open):

        github.GitHub.ssh("people")

        mock_open.assert_called_once_with("/root/.ssh/config", "a")
        mock_open.return_value.__enter__().write.assert_has_calls([
            unittest.mock.call("Host stuff\n"),
            unittest.mock.call("    User things\n"),
            unittest.mock.call("    IdentityFile /root/.ssh/github_people.key\n"),
            unittest.mock.call("    StrictHostKeyChecking no\n"),
            unittest.mock.call("    IdentitiesOnly yes\n")
        ])

        mock_subprocess.assert_has_calls([
            unittest.mock.call("cp /opt/service/secret/github_people.key /root/.ssh/", shell=True),
            unittest.mock.call("chmod 600 /root/.ssh/github_people.key", shell=True)
        ])

    @unittest.mock.patch.dict(github.GitHub.creds, {})
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch('github.open', create=True)
    @unittest.mock.patch('github.GitHub.ssh')
    def test_config(self, mock_ssh, mock_open, mock_glob):

        mock_glob.return_value = ["what/github_people.json"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data='{"stuff": "things"}').return_value
        ]

        github.GitHub.config()

        self.assertEqual(github.GitHub.creds, {
            "people": {
                "stuff": "things",
                "url": "https://api.github.com",
                "host": "github.com"
            }
        })

        mock_ssh.assert_called_once_with("people")

    @unittest.mock.patch.dict(github.GitHub.creds, {
        "default": {
            "user": "arcade",
            "token": "fire",
            "host": "most",
            "url":  "curl"
        }
    })
    def test___init__(self):

        cnc = unittest.mock.MagicMock()
        cnc.data = {
            "output": {
                "github": {
                    "branches": {
                        "arcade/git.com": "tree"
                    }
                }
            }
        }

        init = github.GitHub(cnc, {"repo": "git.com"})

        self.assertEqual(init.cnc, cnc)
        self.assertEqual(init.user, "arcade")
        self.assertEqual(init.host, "most")
        self.assertEqual(init.url, "curl")
        self.assertIsInstance(init.api, requests.Session)
        self.assertEqual(init.api.auth, ("arcade", "fire"))
        self.assertEqual(init.data, {
            "creds": "default",
            "repo": "git.com",
            "name": "git.com",
            "user": "arcade",
            "path": "arcade/git.com",
            "branch": "tree"
        })

        init = github.GitHub(cnc, {
            "repo": "anization/git.com",
            "hook": "captain",
            "comment": "smead"
        })

        self.assertEqual(init.data, {
            "creds": "default",
            "repo": "anization/git.com",
            "org": "anization",
            "name": "git.com",
            "path": "anization/git.com",
            "hook": [
                {
                    "url": "captain"
                },
            ],
            "comment": [
                {
                    "body": "smead"
                }
            ]
        })

    def test_request(self):

        self.github.api.request.return_value.json.return_value = {"a": 1}

        self.assertEqual(self.github.request("GET", "some", {"b": 2}, {"c": 3}), {"a": 1})

        self.github.api.request.assert_called_once_with("GET", "curl/some", params={"b": 2}, json={"c": 3})

        self.github.api.request.return_value.raise_for_status.assert_called_once_with()

    def test_iterate(self):

        # none

        self.github.api.request.return_value.json.return_value = []

        self.assertEqual(list(self.github.iterate("none")), [])

        self.github.api.request.assert_called_once_with("GET", "curl/none", params={"page": 1}, json=None)

        # some

        some = unittest.mock.MagicMock()
        none = unittest.mock.MagicMock()

        some.json.return_value = [{"a": 1}]
        none.json.return_value = []

        self.github.api.request.side_effect = [some, none]

        self.assertEqual(list(self.github.iterate("some", {"b": 2}, {"c": 3})), [{"a": 1}])

        self.github.api.request.assert_has_calls([
            unittest.mock.call("GET", "curl/some", params={"b": 2, "page": 1}, json={"c": 3}),
            unittest.mock.call("GET", "curl/some", params={"b": 2, "page": 2}, json={"c": 3})
        ])

    def test_repo(self):

        # repo exists

        self.github.data = {
            "path": "does/exist",
            "org": "does",
            "name": "exist"
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "full_name": "does/exist",
            "default_branch": "maine"
        }])

        self.github.request = unittest.mock.MagicMock(return_value=[True])

        self.assertTrue(self.github.repo())

        self.assertEqual(self.github.data, {
            "path": "does/exist",
            "org": "does",
            "name": "exist",
            "default": "maine",
            "base": "maine"
        })

        self.github.iterate.assert_called_once_with("user/repos")
        self.github.request.assert_called_once_with("GET", "repos/does/exist/branches")

        # org repo dooesn't exist but don't ensure

        self.github.data = {
            "path": "doesnt/exist",
            "org": "doesnt",
            "name": "exist"
        }

        self.github.request.side_effect = [
            {
                "default_branch": "notracist"
            },
            [
                True
            ]
        ]

        self.assertFalse(self.github.repo(ensure=False))

        self.assertEqual(self.github.data, {
            "path": "doesnt/exist",
            "org": "doesnt",
            "name": "exist"
        })

        # org repo dooesn't exist

        self.github.data = {
            "path": "doesnt/exist",
            "org": "doesnt",
            "name": "exist"
        }

        self.github.request.side_effect = [
            {
                "default_branch": "notracist"
            },
            [
                True
            ]
        ]

        self.github.repo()

        self.assertEqual(self.github.data, {
            "path": "doesnt/exist",
            "org": "doesnt",
            "name": "exist",
            "default": "notracist",
            "base": "notracist"
        })

        self.github.request.assert_has_calls([
            unittest.mock.call("POST", "orgs/doesnt/repos", json={
                "name": "exist",
                "private": True,
                "visibility": "internal"
            })
        ])

        # user repo doesn't exist

        self.github.data = {
            "path": "dont/exist",
            "user": "dont",
            "name": "exist"
        }

        self.github.request.side_effect = [
            {
                "default_branch": "wtfdude"
            },
            [
                True
            ]
        ]

        self.github.repo()

        self.assertEqual(self.github.data, {
            "path": "dont/exist",
            "user": "dont",
            "name": "exist",
            "default": "wtfdude",
            "base": "wtfdude"
        })

        self.github.request.assert_has_calls([
            unittest.mock.call("POST", "user/repos", json={
                "name": "exist",
                "private": True
            })
        ])

        # default branch doesn't exist

        self.github.data = {
            "path": "does/exist",
            "org": "does",
            "name": "exist",
            "title": "heavyweight"
        }

        self.github.request = unittest.mock.MagicMock(return_value=[])

        self.github.repo()

        self.assertEqual(self.github.data, {
            "path": "does/exist",
            "org": "does",
            "name": "exist",
            "title": "heavyweight",
            "default": "maine",
            "base": "maine"
        })

        self.github.request.assert_has_calls([
            unittest.mock.call("PUT", "repos/does/exist/contents/CNC", json={
                "message": "Created by CnC Forge - heavyweight",
                "content": base64.b64encode("Created by CnC Forge - heavyweight".encode('utf-8')).decode('utf-8')
            })
        ])

    def test_hook(self):

        self.github.data = {
            "path": "my/stuff",
            "hook": [
                {"url": "here"},
                {"url": "there"}
            ]
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "config": {"url": "here"}
        }])

        self.github.request = unittest.mock.MagicMock()

        self.github.hook()

        self.github.request.assert_called_with("POST", "repos/my/stuff/hooks", json={
            "config": {"url": "there"}
        })

    @unittest.mock.patch("builtins.print")
    def test_branch(self, mock_print):

        self.github.data = {
            "path": "my/stuff"
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "name": "exists"
        }])

        self.github.request = unittest.mock.MagicMock(return_value={
            "object": {
                "sha": "right"
            }
        })

        self.github.branch("exists", "drum")

        self.github.request.assert_not_called()

        self.github.branch("notexists", "drum")

        self.github.request.assert_called_with("POST", "repos/my/stuff/git/refs", json={
            "ref": f"refs/heads/notexists",
            "sha": "right"
        })

        mock_print.assert_called_once_with({
            "ref": f"refs/heads/notexists",
            "sha": "right"
        })

    @unittest.mock.patch("builtins.print")
    def test_pull_request(self, mock_print):

        self.github.data = {
            "path": "my/stuff",
            "branch": "exists"
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "head": {"ref": "exists"},
            "html_url": "ya"
        }])

        self.github.request = unittest.mock.MagicMock(return_value={
            "html_url": "sure"
        })

        # exists

        self.github.pull_request()

        self.assertEqual(self.github.data, {
            "path": "my/stuff",
            "branch": "exists",
            "url": "ya"
        })

        self.github.request.assert_not_called()

        # doesn't exist

        self.github.data = {
            "path": "my/stuff",
            "branch": "doesntexist",
            "title": "heavyweight",
            "base": "drum"
        }

        self.github.pull_request()

        self.assertEqual(self.github.data, {
            "path": "my/stuff",
            "branch": "doesntexist",
            "title": "heavyweight",
            "base": "drum",
            "url": "sure"
        })

        self.github.request.assert_called_with("POST", "repos/my/stuff/pulls", json={
            "head": "doesntexist",
            "base": "drum",
            "title": "heavyweight"
        })

        mock_print.assert_called_once_with({
            "head": "doesntexist",
            "base": "drum",
            "title": "heavyweight"
        })

    def test_comment(self):

        self.github.data = {
            "path": "my/stuff",
            "url": "pr/7",
            "comment": [
                {"body": "here"},
                {"body": "there"}
            ]
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "body": "here"
        }])

        self.github.request = unittest.mock.MagicMock()

        self.github.comment()

        self.github.request.assert_called_with("POST", "repos/my/stuff/issues/7/comments", json={
            "body": "there"
        })

    @unittest.mock.patch("os.chdir")
    @unittest.mock.patch("shutil.rmtree")
    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("subprocess.check_output")
    def test_change(self, mock_subprocess, mock_print, mock_rmtree, mock_chdir):

        mock_subprocess.side_effect = ["cloned", "checked out"]

        self.github.cnc = unittest.mock.MagicMock()
        self.github.cnc.data = {}
        self.github.cnc.base.return_value = "noise"

        self.github.data = {
            "path": "my/stuff",
            "branch": "ayup"
        }

        self.github.change()

        self.assertEqual(self.github.cnc.data["change"], self.github.data)

        mock_chdir.assert_has_calls([
            unittest.mock.call("noise"),
            unittest.mock.call("noise/source")
        ])
        mock_rmtree.assert_called_once_with("noise/source", ignore_errors=True)
        mock_subprocess.assert_has_calls([
            unittest.mock.call("git clone git@most:my/stuff.git source", shell=True),
            unittest.mock.call("git checkout ayup", shell=True)
        ])
        mock_print.assert_has_calls([
            unittest.mock.call("cloned"),
            unittest.mock.call("checked out")
        ])

        # again

        mock_chdir.reset_mock()

        self.github.change()

        mock_chdir.assert_not_called()

    @unittest.mock.patch("os.chdir")
    @unittest.mock.patch("shutil.rmtree")
    @unittest.mock.patch("os.makedirs")
    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("subprocess.check_output")
    def test_code(self, mock_subprocess, mock_print, mock_makedirs, mock_rmtree, mock_chdir):

        self.github.cnc = unittest.mock.MagicMock()
        self.github.repo = unittest.mock.MagicMock()
        self.github.hook = unittest.mock.MagicMock()
        self.github.branch = unittest.mock.MagicMock()

        self.github.cnc.data = {"id": "sweat", "action": "test"}
        self.github.cnc.base.return_value = "noise"

        self.github.data = {
            "path": "my/stuff",
            "prefix": "mr",
            "default": "def",
            "base": "drum"
        }

        mock_subprocess.side_effect = ["cloned", "checked out"]

        # test

        self.github.repo.return_value = False

        self.github.code()

        mock_chdir.assert_has_calls([
            unittest.mock.call("noise")
        ])
        mock_rmtree.assert_called_once_with("noise/destination", ignore_errors=True)
        mock_makedirs.assert_called_once_with("noise/destination")

        self.assertEqual(self.github.data, {
            "path": "my/stuff",
            "prefix": "mr",
            "default": "def",
            "base": "drum",
            "branch": "mr-sweat",
            "title": "mr-sweat"
        })

        self.github.repo.assert_called_once_with(ensure=False)
        self.github.hook.assert_not_called()
        self.github.branch.assert_not_called()

        # commit

        self.github.repo.return_value = True
        self.github.cnc.data["action"] = "commit"

        self.github.code()

        self.assertEqual(self.github.data, {
            "path": "my/stuff",
            "prefix": "mr",
            "default": "def",
            "base": "drum",
            "branch": "mr-sweat",
            "title": "mr-sweat"
        })

        self.github.repo.assert_called_with(ensure=True)
        self.github.hook.assert_called_once_with()
        self.github.branch.assert_has_calls([
            unittest.mock.call("drum", "def"),
            unittest.mock.call("mr-sweat", "drum"),
        ])

        mock_subprocess.assert_has_calls([
            unittest.mock.call("git clone git@most:my/stuff.git destination", shell=True),
            unittest.mock.call("git checkout mr-sweat", shell=True)
        ])
        mock_print.assert_has_calls([
            unittest.mock.call("cloned"),
            unittest.mock.call("checked out")
        ])

        mock_chdir.assert_has_calls([
            unittest.mock.call("noise"),
            unittest.mock.call("noise/destination")
        ])

    @unittest.mock.patch("os.chdir")
    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("os.rename")
    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("subprocess.check_output")
    def test_commit(self, mock_subprocess, mock_print, mock_rename, mock_exists, mock_chdir):

        self.github.data = {"url": "sure"}

        self.github.cnc = unittest.mock.MagicMock()
        self.github.link = unittest.mock.MagicMock()
        self.github.pull_request = unittest.mock.MagicMock()
        self.github.comment = unittest.mock.MagicMock()

        self.github.cnc.data = {"id": "sweat", "action": "test"}
        self.github.cnc.base.return_value = "noise"

        def exists(path):

            return path.endswith("code-0")

        mock_exists.side_effect = exists

        git_status = b"Changes to be committed"

        def subprocess(command, shell):

            if command.startswith("git add"):
                return "added"
            elif command.startswith("git status"):
                return git_status
            elif command.startswith("git commit"):
                return "committed"
            elif command.startswith("git push"):
                return "pushed"

        mock_subprocess.side_effect = subprocess

        # test

        self.github.commit()

        mock_chdir.assert_has_calls([
            unittest.mock.call("noise/destination")
        ])
        mock_rename.assert_called_once_with(
            "noise/destination",
            "noise/code-1"
        )
        mock_subprocess.assert_not_called()

        # commit

        self.github.cnc.data["action"] = "commit"

        self.github.commit()

        self.github.cnc.link.assert_called_once_with("sure")

        mock_subprocess.assert_has_calls([
            unittest.mock.call("git add .", shell=True),
            unittest.mock.call("git status", shell=True),
            unittest.mock.call("git commit -am 'sweat'", shell=True),
            unittest.mock.call("git push origin", shell=True)
        ])
        mock_print.assert_has_calls([
            unittest.mock.call("added"),
            unittest.mock.call("committed"),
            unittest.mock.call("pushed")
        ])
