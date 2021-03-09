"""
Module for interacting with GitHub
"""

import os
import shutil
import requests
import subprocess

class GitHub:
    """
    Class for interacting with GitHub
    """

    def __init__(self, user, token, url="https://api.github.com"):

        self.user = user
        self.token = token
        self.api = requests.Session()
        self.api.auth = (self.user, self.token)
        self.url = url

    def request(self, method, path, params=None, json=None):
        """
        Performs a request and return the JSON
        """

        response = self.api.request(method, f"{self.url}/{path}", params=params, json=json)

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

    def repo(self, repo, ensure=True):
        """
        Ensure a repo exists, whether org or user
        """

        if isinstance(repo, str):
            if "/" in repo:
                repo = {"full_name": repo}
                repo["org"], repo["name"] = repo["full_name"].split("/")
            else:
                repo = {"name": repo}

        if "full_name" not in repo:
            repo["full_name"] = f"{repo.get('org') or self.user}/{repo['name']}"

        for exists in self.iterate("user/repos"):
            if exists["full_name"] == repo["full_name"]:
                repo.setdefault("base_branch", exists["default_branch"])
                repo["url"] = exists["html_url"]
                return repo

        if not ensure:
            return repo

        repo.setdefault("private", True)

        if repo.get('org'):
            path = f"orgs/{repo['org']}/repos"
            repo.setdefault("visibility", "internal")
        else:
            path = "user/repos"

        created = self.request("POST", path, json=dict(repo))

        repo.setdefault("base_branch", created["default_branch"])
        repo["url"] = created["html_url"]

        return repo

    def hook(self, repo, hooks):
        """
        Ensure one or more hooks are on a repo
        """

        if isinstance(hooks, str):
            hooks = [hooks]

        hooks = [{"url": hook} if isinstance(hook, str) else hook for hook in hooks]

        exists = [hook["config"]["url"] for hook in self.iterate(f"repos/{repo['full_name']}/hooks")]

        for hook in hooks:

            if hook['url'] in exists:
                continue

            self.request("POST", f"repos/{repo['full_name']}/hooks", json={"config": hook})

        return hooks

    def pull_request(self, repo, branch, pull_request):
        """
        Ensures a pull request exists
        """

        if isinstance(pull_request, str):
            pull_request = {"title": pull_request}
        else:
            pull_request.setdefault("title", branch)

        for exists in self.iterate(f"repos/{repo['full_name']}/pulls"):
            if exists["head"]["ref"] == branch:
                pull_request["url"] = exists["html_url"]
                return pull_request

        create = {
            "head": branch,
            "base": repo['base_branch'],
            **pull_request
        }

        print(create)

        pull_request["url"] = self.request("POST", f"repos/{repo['full_name']}/pulls", json=create)["html_url"]

        return pull_request

    def clone(self, cnc, github):
        """
        Clones a repo for a code block unless we're testing, then just creates a directory
        """

        os.chdir(cnc.base())

        destination = f"{cnc.base()}/destination"

        shutil.rmtree(destination, ignore_errors=True)

        # Get the repo info and don't bother creating if we're testing

        github["repo"] = self.repo(github["repo"], ensure=not cnc.data["test"])

        # If there's not base_branch, there's no repo, so just make the destination directory and split

        if "base_branch" not in github["repo"]:
            os.makedirs(destination)
            return

        if "hook" in github:
            github["hook"] = self.hook(github["repo"], github["hook"])

        print(subprocess.check_output(f"git clone git@github.com:{github['repo']['full_name']}.git destination", shell=True))

        branch = f"{github['prefix']}-{cnc.data['id']}" if "prefix" in github else cnc.data["id"]

        github.setdefault("branch", branch)

        os.chdir(destination)

        if github['branch'].encode() not in subprocess.check_output("git branch", shell=True):
            github['upstream'] = True
            print(subprocess.check_output(f"git checkout -b {github['branch']}", shell=True))
        else:
            print(subprocess.check_output(f"git checkout {github['branch']}", shell=True))

    def change(self, cnc, github):
        """
        Clones a repo for a change block
        """

        github["repo"] = self.repo(github["repo"], ensure=False)

        # If this is the last repo/branch, just repo it again

        if cnc.data.get("change") == github:
            return

        cnc.data["change"] = github

        os.chdir(cnc.base())

        source = f"{cnc.base()}/source"

        shutil.rmtree(source, ignore_errors=True)

        print(subprocess.check_output(f"git clone git@github.com:{github['repo']['full_name']}.git source", shell=True))

        if github.get("branch") and github["branch"] != github["repo"]["base_branch"]:
            os.chdir(source)
            print(subprocess.check_output(f"git checkout {github['branch']}", shell=True))

    def commit(self, cnc, github):
        """
        Commits a repo for a code block
        """

        destination = f"{cnc.base()}/destination"

        os.chdir(destination)

        # If we're testing, move a code-# dir

        if cnc.data["test"]:

            code = 0

            while os.path.exists(f"{cnc.base()}/code-{code}"):
                code += 1

            os.rename(destination, f"{cnc.base()}/code-{code}")

            return

        print(subprocess.check_output("git add .", shell=True))

        if b"Changes to be committed" in subprocess.check_output("git status", shell=True):

            message = f"{github['prefix']}: {cnc.data['id']}" if "prefix" in github else cnc.data["id"]

            print(subprocess.check_output(f"git commit -am '{message}'", shell=True))

            if github.get("upstream"):
                print(subprocess.check_output(f"git push --set-upstream origin {github['branch']}", shell=True))
            else:
                print(subprocess.check_output("git push origin", shell=True))

        if github.get("branch") != github["repo"]["base_branch"]:
            github["pull_request"] = self.pull_request(github["repo"], github["branch"], github.get("pull_request", github["branch"]))
            cnc.link(github["pull_request"]["url"])
        else:
            cnc.link(github["repo"]["url"])
