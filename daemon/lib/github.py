""" Module for interacting with GitHub """

import requests
import subprocess

class GitHub:
    """ Class for interacting with GitHub """

    def __init__(self, user, token, url="https://api.github.com"):

        self.user = user
        self.token = token
        self.api = requests.Session()
        self.api.auth = (self.user, self.token)
        self.url = url

        self.user = self.request("GET", "user")["login"]

    def request(self, method, path, params=None, json=None, verify=True):
        """ Performs a request and return the JSON """

        response = self.api.request(method, f"{self.url}/{path}", params=params, json=json)

        if verify:
            response.raise_for_status()

        return response.json()

    def iterate(self, path, params=None, json=None):
        """ Iterate through all results """

        if params is None:
            params = {}

        params["page"] = 1

        results = self.request("GET", path, params, json)

        while results:
            for result in results:
                yield result
            params["page"] += 1
            results = self.request("GET", path, params, json)

    def repo(self, repo, ensure=True):
        """ Ensure a repo exists, whether org or user """

        if isinstance(repo, str):
            if "/" in repo:
                repo = {"full_name": repo}
                repo["org"], repo["name"] = repo["full_name"].split("/")
            else:
                repo = {"name": repo}

        if "full_name" not in repo:
            repo["full_name"] = f"{repo.get('org') or self.user}/{repo['name']}"

        if not ensure:
            return repo

        for exists in self.iterate("user/repos"):
            if exists["full_name"] == repo["full_name"]:
                repo.setdefault("base_branch", exists["default_branch"])
                repo["init"] = len(self.request(f"repos/{repo['full_name']}/branches")) == 0
                return repo

        repo.setdefault("private", True)

        if repo.get('org'):
            path = f"orgs/{repo['org']}/repos"
            repo.setdefault("visibility", "internal")
        else:
            path = f"user/repos"

        repo.setdefault("base_branch", self.request("POST", path, json=repo)["dafault_branch"])

        return repo

    def branch(self, repo, branch):
        """ Ensures a branch exists """

        for exsits in self.iterate(f"repos/{repo['full_name']}/branches"):
            if exsits["name"] == branch:
                return branch

        sha = self.request("GET", f"repos/{repo['full_name']}/branches/{repo['base_branch']}")["commit"]["sha"]

        self.request("POST", f"repos/{repo['full_name']}/git/refs", json={
            "ref": f"refs/heads/{branch}",
            "sha": sha
        })

        return branch

    def pull_request(self, repo, branch, pull_request):
        """ Ensures a pull request exists """

        if isinstance(pull_request, str):
            pull_request = {"title": pull_request}
        else:
            pull_request.setdefault("title", pull_request)

        for exsits in self.iterate(f"repos/{repo['full_name']}/pulls"):
            if exsits["head"]["ref"] == branch:
                return pull_request

        self.request("POST", f"repos/{repo['full_name']}/pulls", json={
            "head": branch,
            "sha": repo['base_branch'],
            "title": pull_request["title"]
        })

        return pull_request

    def code(self, cnc, code, github):

        github["repo"] = self.repo(github["repo"])

        if github.get("branch") != github["base_branch"]:
            github["branch"] = self.branch(
                github["repo"], github.get("branch", cnc["id"])
            )
            github["pull_request"] = self.branch(
                github["repo"], github["branch"], github["branch"]
            )

        subprocess.check_output(f"rm -rf destination")
        subprocess.check_output(f"git clone git@github.com:{github['repo']['full_name']}.git destination")

        if not github["init"]:
            subprocess.check_output(f"pushd destination && git checkout {github['branch']} && popd")

    def change(self, cnc, code, github):

        github["repo"] = self.github.repo(github["repo"], ensure=False)

        subprocess.check_output(f"rm -rf /opt/service/source")
        subprocess.check_output(f"git clone git@github.com:{github['repo']['full_name']}.git /opt/service/source")

        if "branch" in github:
            subprocess.check_output(f"pushd /opt/service/source && git checkout {github['branch']} && popd")
