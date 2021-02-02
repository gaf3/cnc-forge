import unittest
import unittest.mock

import github

class TestGitHub(unittest.TestCase):

    def setUp(self):

        self.github = github.GitHub("me", "arcade")
        self.github.api = unittest.mock.MagicMock()

    def test___init__(self):

        init = github.GitHub("me", "arcade", "git.com")

        self.assertEqual(init.user, "me")
        self.assertEqual(init.token, "arcade")
        self.assertEqual(init.api.auth, ("me", "arcade"))
        self.assertEqual(init.url, "git.com")

    def test_request(self):

        self.github.api.request.return_value.json.return_value = {"a": 1}

        self.assertEqual(self.github.request("GET", "some", {"b": 2}, {"c": 3}), {"a": 1})

        self.github.api.request.assert_called_once_with("GET", "https://api.github.com/some", params={"b": 2}, json={"c": 3})

        self.github.api.request.return_value.raise_for_status.assert_called_once_with()

    def test_iterate(self):

        # none

        self.github.api.request.return_value.json.return_value = []

        self.assertEqual(list(self.github.iterate("none")), [])

        self.github.api.request.assert_called_once_with("GET", "https://api.github.com/none", params={"page": 1}, json=None)

        # some

        some = unittest.mock.MagicMock()
        none = unittest.mock.MagicMock()

        some.json.return_value = [{"a": 1}]
        none.json.return_value = []

        self.github.api.request.side_effect = [some, none]

        self.assertEqual(list(self.github.iterate("some", {"b": 2}, {"c": 3})), [{"a": 1}])

        self.github.api.request.assert_has_calls([
            unittest.mock.call("GET", "https://api.github.com/some", params={"b": 2, "page": 1}, json={"c": 3}),
            unittest.mock.call("GET", "https://api.github.com/some", params={"b": 2, "page": 2}, json={"c": 3})
        ])

    def test_repo(self):

        # org exists

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "full_name": "does/exist",
            "default_branch": "maine"
        }])

        self.assertEqual(self.github.repo("does/exist"), {
            "full_name": "does/exist",
            "org": "does",
            "name": "exist",
            "base_branch": "maine"
        })

        self.github.iterate.assert_called_once_with("user/repos")

        # users doesn't exist, don't create

        self.assertEqual(self.github.repo("doesnt", False), {
            "full_name": "me/doesnt",
            "name": "doesnt"
        })

        # org dooesn't exist, create

        self.github.api.request.return_value.json.return_value = {"default_branch": "notracist"}

        self.assertEqual(self.github.repo("doesnt/exist"), {
            "full_name": "doesnt/exist",
            "org": "doesnt",
            "name": "exist",
            "private": True,
            "visibility": "internal",
            "base_branch": "notracist"
        })

        self.github.api.request.assert_called_once_with("POST", "https://api.github.com/orgs/doesnt/repos", params=None, json={
            "full_name": "doesnt/exist",
            "org": "doesnt",
            "name": "exist",
            "private": True,
            "visibility": "internal"
        })

        # users doesn't exist, create

        self.assertEqual(self.github.repo("doesnt"), {
            "full_name": "me/doesnt",
            "name": "doesnt",
            "private": True,
            "base_branch": "notracist"
        })

        self.github.api.request.assert_called_with("POST", "https://api.github.com/user/repos", params=None, json={
            "full_name": "me/doesnt",
            "name": "doesnt",
            "private": True
        })

    def test_hook(self):

        repo = {
            "full_name": "my/stuff"
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "config": {"url": "here"}
        }])

        # exists

        self.assertEqual(self.github.hook(repo, "here"), [
            {"url": "here"}
        ])

        self.github.iterate.assert_called_once_with("repos/my/stuff/hooks")

        self.github.api.request.assert_not_called()

        # doesn't exist

        self.assertEqual(self.github.hook(repo, [{"url": "there"}]), [
            {"url": "there"}
        ])

        self.github.api.request.assert_called_with("POST", "https://api.github.com/repos/my/stuff/hooks", params=None, json={
            "config": {"url": "there"}
        })

    def test_branch(self):

        repo = {
            "full_name": "my/stuff",
            "base_branch": "maine"
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "name": "exists"
        }])

        # exists

        self.assertEqual(self.github.branch(repo, "exists"), "exists")

        self.github.iterate.assert_called_once_with("repos/my/stuff/branches")

        # doesn't exist

        self.github.api.request.return_value.json.return_value = {"commit": {"sha": "right"}}

        self.assertEqual(self.github.branch(repo, "doesnt"), "doesnt")

        self.github.api.request.assert_has_calls([
            unittest.mock.call("GET", "https://api.github.com/repos/my/stuff/branches/maine", params=None, json=None),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json(),
            unittest.mock.call("POST", "https://api.github.com/repos/my/stuff/git/refs", params=None, json={
                "ref": "refs/heads/doesnt",
                "sha": "right"
            }),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])

    @unittest.mock.patch("builtins.print")
    def test_pull_request(self, mock_print):

        repo = {
            "full_name": "my/stuff",
            "base_branch": "maine"
        }

        self.github.iterate = unittest.mock.MagicMock(return_value=[{
            "head": {"ref": "exists"}
        }])

        # exists

        self.assertEqual(self.github.pull_request(repo, "exists", "exists"), {
            "title": "exists"
        })

        self.github.iterate.assert_called_once_with("repos/my/stuff/pulls")

        mock_print.assert_not_called()

        # doesn't exist

        self.assertEqual(self.github.pull_request(repo, "doesnt", {"body": "rock"}), {
            "title": "doesnt",
            "body": "rock"
        })

        mock_print.assert_called_once_with({
            "head": "doesnt",
            "base": "maine",
            "title": "doesnt",
            "body": "rock"
        })

        self.github.api.request.assert_has_calls([
            unittest.mock.call("POST", "https://api.github.com/repos/my/stuff/pulls", params=None, json={
                "head": "doesnt",
                "base": "maine",
                "title": "doesnt",
                "body": "rock"
            }),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])

    @unittest.mock.patch("os.chdir")
    @unittest.mock.patch("shutil.rmtree")
    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("subprocess.check_output")
    def test_clone(self, mock_subprocess, mock_print, mock_rmtree, mock_chdir):

        def iterate(url):

            if url == "user/repos":
                return [{
                    "full_name": "my/stuff",
                    "default_branch": "maine"
                }]
            elif url == "repos/my/stuff/hooks":
                return [{
                    "config": {"url": "here"}
                }]
            elif url == "repos/my/stuff/branches":
                return [{
                    "name": "sweat"
                }]

        self.github.iterate = iterate

        git_branch = b"maine"

        def subprocess(command, shell):

            if command.startswith("git clone"):
                return "cloned"
            elif command.startswith("git branch"):
                return git_branch
            elif command.startswith("git checkout"):
                return "checked out"

        mock_subprocess.side_effect = subprocess

        # default branch

        cnc = unittest.mock.MagicMock()

        cnc.data = {"id": "sweat"}
        cnc.base.return_value = "noise"
        cnc.destination.return_value = "dest"

        github = {
            "repo": "my/stuff",
            "branch": "maine",
            "hook": "here"
        }

        self.github.clone(cnc, github)

        self.assertEqual(github, {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "hook": [{
                "url": "here"
            }],
            "branch": "maine"
        })

        cnc.base.assert_called_once_with()
        mock_chdir.assert_has_calls([
            unittest.mock.call("noise"),
            unittest.mock.call("dest")
        ])
        cnc.destination.assert_called_once_with("", path=True)
        mock_rmtree.assert_called_once_with("dest", ignore_errors=True)
        mock_subprocess.assert_has_calls([
            unittest.mock.call("git clone git@github.com:my/stuff.git destination", shell=True),
            unittest.mock.call("git branch", shell=True),
            unittest.mock.call("git checkout maine", shell=True)
        ])
        mock_print.assert_has_calls([
            unittest.mock.call("cloned"),
            unittest.mock.call("checked out")
        ])

        # new branch

        github = {
            "repo": "my/stuff",
            "hook": "here"
        }

        self.github.clone(cnc, github)

        self.assertEqual(github, {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "hook": [{
                "url": "here"
            }],
            "branch": "sweat",
            "upstream": True
        })

        mock_subprocess.assert_has_calls([
            unittest.mock.call("git clone git@github.com:my/stuff.git destination", shell=True),
            unittest.mock.call("git branch", shell=True),
            unittest.mock.call("git checkout -b sweat", shell=True)
        ])

    @unittest.mock.patch("os.chdir")
    @unittest.mock.patch("shutil.rmtree")
    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("subprocess.check_output")
    def test_change(self, mock_subprocess, mock_print, mock_rmtree, mock_chdir):

        def iterate(url):

            if url == "user/repos":
                return [{
                    "full_name": "my/stuff",
                    "default_branch": "maine"
                }]

        self.github.iterate = iterate

        def subprocess(command, shell):

            if command.startswith("git clone"):
                return "cloned"
            elif command.startswith("git checkout"):
                return "checked out"

        mock_subprocess.side_effect = subprocess

        # different branch

        cnc = unittest.mock.MagicMock()

        cnc.base.return_value = "noise"
        cnc.source.return_value = "src"

        github = {
            "repo": "my/stuff",
            "branch": "ayup"
        }

        self.github.change(cnc, github)

        self.assertEqual(github, {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "branch": "ayup"
        })

        cnc.base.assert_called_once_with()
        mock_chdir.assert_has_calls([
            unittest.mock.call("noise"),
            unittest.mock.call("src")
        ])
        cnc.source.assert_called_once_with("", path=True)
        mock_rmtree.assert_called_once_with("src", ignore_errors=True)
        mock_subprocess.assert_has_calls([
            unittest.mock.call("git clone git@github.com:my/stuff.git source", shell=True),
            unittest.mock.call("git checkout ayup", shell=True)
        ])
        mock_print.assert_has_calls([
            unittest.mock.call("cloned"),
            unittest.mock.call("checked out")
        ])

    @unittest.mock.patch("os.chdir")
    @unittest.mock.patch("builtins.print")
    @unittest.mock.patch("subprocess.check_output")
    def test_commit(self, mock_subprocess, mock_print, mock_chdir):

        def iterate(url):

            if url == "repos/my/stuff/pulls":
                return [{
                    "head": {"ref": "ayup"}
                }]

        self.github.iterate = iterate

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

        # new

        cnc = unittest.mock.MagicMock()

        cnc.data = {"id": "sweat"}
        cnc.destination.return_value = "dest"

        github = {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "branch": "ayup",
            "upstream": True
        }

        self.github.commit(cnc, github)

        self.assertEqual(github, {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "branch": "ayup",
            "upstream": True,
            "pull_request": {
                "title": "ayup"
            }
        })

        cnc.destination.assert_called_once_with("", path=True)
        mock_chdir.assert_has_calls([
            unittest.mock.call("dest")
        ])
        mock_subprocess.assert_has_calls([
            unittest.mock.call("git add .", shell=True),
            unittest.mock.call("git status", shell=True),
            unittest.mock.call("git commit -am 'sweat'", shell=True),
            unittest.mock.call("git push --set-upstream origin ayup", shell=True)
        ])
        mock_print.assert_has_calls([
            unittest.mock.call("added"),
            unittest.mock.call("committed"),
            unittest.mock.call("pushed")
        ])

        # old

        github = {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "branch": "maine"
        }

        self.github.commit(cnc, github)

        self.assertEqual(github, {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "branch": "maine"
        })

        mock_subprocess.assert_has_calls([
            unittest.mock.call("git add .", shell=True),
            unittest.mock.call("git status", shell=True),
            unittest.mock.call("git commit -am 'sweat'", shell=True),
            unittest.mock.call("git push origin", shell=True)
        ])

        # no changes

        mock_subprocess.reset_mock()

        git_status = b"All good"

        github = {
            "repo": {
                "full_name": "my/stuff",
                "org": "my",
                "name": "stuff",
                "base_branch": "maine"
            },
            "branch": "maine"
        }

        self.github.commit(cnc, github)

        mock_subprocess.assert_has_calls([
            unittest.mock.call("git add .", shell=True),
            unittest.mock.call("git status", shell=True)
        ])
