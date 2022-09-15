"""
Module for interacting with GitHub
"""

import os
import shutil
import base64
import requests
import subprocess


class GitHub:
    """
    Class for interacting with GitHub
    data fields:
        api: API to use set by the user
        repo: repo from settings
        name: name of the repo
        org: IF there's an org to do
        user: If this is owned by a user
        path: Full path to access the repo
        hook: The hook(s) to use
        prefix: Prefix to use for branch and title
        title: Title for the PR
        default: THe default branch of the repo
        branch: THe branch for the PR
        base: The base branch of the PR
        url: The pull equest url
    """

    data = None

    def __init__(self, cnc, creds, data):

        self.cnc = cnc
        self.user = creds['user']
        self.api = requests.Session()
        self.api.auth = (self.user, creds['token'])
        self.data = data

        self.data.setdefault("api", "https://api.github.com")

        if isinstance(self.data["repo"], str):

            if "/" in self.data["repo"]:
                self.data["path"] = self.data["repo"]
                self.data["org"], name = self.data["repo"].split("/")
            else:
                self.data["path"] = f"{self.user}/{self.data['repo']}"
                self.data["user"] = self.user
                name = self.data['repo']

            self.data.setdefault("name", name)
            self.data.setdefault("path", f"{self.data.get('org') or self.data['user']}/{name}")

        if "hook" in self.data:

            if isinstance(self.data["hook"], str):
                self.data["hook"] = [self.data["hook"]]

            self.data["hook"] = [{"url": hook} if isinstance(hook, str) else hook for hook in self.data["hook"]]

    def request(self, method, path, params=None, json=None):
        """
        Performs a request and return the JSON
        """

        response = self.api.request(method, f"{self.data['api']}/{path}", params=params, json=json)

        response.raise_for_status()

        return response.json()

    def iterate(self, path, params=None, json=None):
        """
        Iterate through all results
        """

        if params is None:
            params = {}

        params["page"] = 1

        results = self.request("GET", path, params, json)

        while results:
            for result in results:
                yield result
            params = {**params, "page": params["page"] + 1}
            results = self.request("GET", path, params, json)

    def repo(self):
        """
        Ensure a repo exists, and can be checked out and committed against
        """

        # First make sure the repo exists

        found = False

        for exists in self.iterate("user/repos"):

            if exists["full_name"] == self.data["path"]:
                self.data["default"] = exists["default_branch"]
                found = True

        if not found:

            create = {
                "name": self.data["name"],
                "private": True
            }

            if self.data.get('org'):
                path = f"orgs/{self.data['org']}/repos"
                create["visibility"] = "internal"
            else:
                path = "user/repos"

            created = self.request("POST", path, json=create)

            self.data["default"] = created["default_branch"]

        # Now make sure it has a default branch and can be cloned

        if not self.request("GET", f"repos/{self.data['path']}/branches"):
            message = f"Created by CnC Forge - {self.data['title']}"
            self.request("PUT", f"repos/{self.data['path']}/contents/CNC", json={
                "message": message,
                "content": base64.b64encode(message.encode('utf-8')).decode('utf-8')
            })

        # Now that we know the default we can set the base

        self.data.setdefault("base", self.data["default"])

    def hook(self):
        """
        Ensure one or more hooks are on a repo
        """

        exists = [hook["config"]["url"] for hook in self.iterate(f"repos/{self.data['path']}/hooks")]

        for hook in self.data.get("hook", []):

            if hook['url'] in exists:
                continue

            self.request("POST", f"repos/{self.data['path']}/hooks", json={"config": hook})

    def branch(self, branch, base):
        """
        Ensure a branch exists
        """

        for exists in self.iterate(f"repos/{self.data['path']}/branches"):
            if exists["name"] == branch:
                return

        sha = self.request("GET", f"repos/{self.data['path']}/git/refs/heads/{base}")["object"]["sha"]

        create = {
            "ref": f"refs/heads/{branch}",
            "sha": sha
        }

        print(create)

        self.request("POST", f"repos/{self.data['path']}/git/refs", json=create)

    def pull_request(self):
        """
        Ensures a pull request exists, including the need branches
        """

        for exists in self.iterate(f"repos/{self.data['path']}/pulls"):
            if exists["head"]["ref"] == self.data['branch']:
                self.data["url"] = exists["html_url"]
                return

        create = {
            "head": self.data['branch'],
            "base": self.data["base"],
            "title": self.data["title"]
        }

        print(create)

        self.data["url"] = self.request("POST", f"repos/{self.data['path']}/pulls", json=create)["html_url"]

    def change(self):
        """
        Clones a repo for a change block
        """

        # If this is the same as the last repo/branch, just repo it again

        if self.cnc.data.get("change") == self.data:
            return

        self.cnc.data["change"] = self.data

        os.chdir(self.cnc.base())

        source = f"{self.cnc.base()}/source"

        shutil.rmtree(source, ignore_errors=True)

        print(subprocess.check_output(f"git clone git@github.com:{self.data['path']}.git source", shell=True))

        if "branch" in self.data:
            os.chdir(source)
            print(subprocess.check_output(f"git checkout {self.data['branch']}", shell=True))

    def code(self):
        """
        Clones a repo for a code block unless we're testing, then just creates a directory
        """

        os.chdir(self.cnc.base())

        destination = f"{self.cnc.base()}/destination"

        shutil.rmtree(destination, ignore_errors=True)

        # If we're testing, just make the directory

        if self.cnc.data["test"]:
            os.makedirs(destination)
            return

        # Set some defaults for branches

        branch = f"{self.data['prefix']}-{self.cnc.data['id']}" if "prefix" in self.data else self.cnc.data["id"]

        self.data.setdefault("branch", branch)
        self.data.setdefault("title", branch)

        # Make sure the repo exists and has a default branch

        self.repo()

        # Make sure hooks are there

        self.hook()

        # Make sure we have all the branches we need

        self.branch(self.data["base"], self.data['default'])
        self.branch(self.data["branch"], self.data['base'])

        print(subprocess.check_output(f"git clone git@github.com:{self.data['path']}.git destination", shell=True))

        os.chdir(destination)

        print(subprocess.check_output(f"git checkout {self.data['branch']}", shell=True))

    def commit(self):
        """
        Commits a repo for a code block
        """

        destination = f"{self.cnc.base()}/destination"

        os.chdir(destination)

        # If we're testing, move a code-# dir

        if self.cnc.data["test"]:

            code = 0

            while os.path.exists(f"{self.cnc.base()}/code-{code}"):
                code += 1

            os.rename(destination, f"{self.cnc.base()}/code-{code}")

            return

        print(subprocess.check_output("git add .", shell=True))

        if b"Changes to be committed" in subprocess.check_output("git status", shell=True):

            message = f"{self.data['prefix']}: {self.cnc.data['id']}" if "prefix" in self.data else self.cnc.data["id"]

            print(subprocess.check_output(f"git commit -am '{message}'", shell=True))

            print(subprocess.check_output("git push origin", shell=True))

        # Make sure there's a pull request

        self.pull_request()

        self.cnc.link(self.data['url'])
