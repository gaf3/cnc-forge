"""
Main module for daemon
"""

import os
import json
import time
import fnmatch
import traceback
import subprocess

import redis
import jinja2
import github

class Daemon:
    """
    Main class for daemon
    """

    def __init__(self):

        self.sleep = float(os.environ['SLEEP'])

        with open("/opt/service/secret/redis.json", "r") as redis_file:
            self.redis = redis.Redis(charset="utf-8", decode_responses=True, **json.loads(redis_file.read()))

        with open("/opt/service/secret/github.json", "r") as github_file:
            self.github = github.GitHub(**json.loads(github_file.read()))

        subprocess.check_output("mkdir -p /root/.ssh", shell=True)
        subprocess.check_output("cp /opt/service/secret/.sshconfig /root/.ssh/config", shell=True)
        subprocess.check_output("cp /opt/service/secret/.gitconfig /root/.gitconfig", shell=True)

        self.env = jinja2.Environment()

    def transform(self, template, values):

        if isinstance(template, str):
            return self.env.from_string(template).render(**values)
        if isinstance(template, list):
            return [self.transform(item, values) for item in template]
        if isinstance(template, dict):
            return {key: self.transform(item, values) for key, item in template.items()}

    def preserve(self, path, patterns):

        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return True

    def load(self, location, path):

        with open(f"/opt/service/{location}/{path}", "r") as load_file:
            return load_file.read()

    def craft(self, cnc, code, change, source, destination, preserve):

        if os.path.isdir(source):
            for item in os.listdir(source):
                self.craft(cnc, code, change, f"{source}/item", f"{desintation}/item", preserve)
            return

        product = self.load("source", source)

        if not self.preserve(source, preserve):
            product = self.transform(product, cnc["values"])

        with open(f"/opt/service/destination/{destination}", "r") as product_file:
            return product_file.write(product)

    def content(self, cnc, code, change, content):

        content["source"] = self.transform(content["source"], cnc["values"])
        content["destination"] = self.transform(content["destination"], cnc["values"])
        content["preserve"] = self.transform(content.get("preserve", []), cnc["values"])

        if isinstance(content["preserve"], str):
            content["perserve"] = [content["preserve"]]

        self.craft(cnc, code, change, content["source"], content["destination"], content["preserve"])

    def change(self, cnc, code, change):

        if "github" in change:
            github["repo"] = self.transform(github["repo"], cnc["values"])
            self.github.change(cnc, code, code["github"])

        for content in change["content"]:
            self.content(cnc, code, change, content)

    def code(self, cnc, code):

        if "github" in code:
            github["repo"] = self.transform(github["repo"], cnc["values"])
            self.github.code(cnc, code, code["github"])

        for change in code["change"]:
            self.change(cnc, code, change)

    def cnc(self, cnc):

        cnc["code"] = cnc["output"]["code"]

        for code in cnc["code"]:
            self.code(cnc, code)

        cnc["status"] = "Completed"

    def process(self):
        """
        Processes all the routines for reminding
        """

        for key in self.redis.keys("/cnc/*"):

            cnc = json.loads(self.redis.get(key))

            if cnc["status"] not in ["Created", "Retry"]:
                continue

            try:
                self.cnc(cnc)
            except Exception as exception:
                cnc["status"] = "Error"
                cnc["error"] = str(exception)
                cnc["traceback"] = traceback.format_exc()

            self.redis.set(key, json.dumps(cnc), ex=24*60*60)

    def run(self):
        """
        Runs the daemon
        """

        while True:
            self.process()
            time.sleep(self.sleep)
