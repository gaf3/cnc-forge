"""
Main module for daemon
"""

import os
import json
import time
import shutil
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
        subprocess.check_output("cp /opt/service/secret/github.key /root/.ssh/", shell=True)
        subprocess.check_output("chmod 600 /root/.ssh/github.key", shell=True)
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

    def iterate(self, items, values):

        for item in items:
            if "condition" not in item or self.transform(item["condition"], values):
                yield item, values

    def exclude(self, content):

        for pattern in content['include']:
            if fnmatch.fnmatch(content['source'], pattern):
                return False

        for pattern in content['exclude']:
            if fnmatch.fnmatch(content['source'], pattern):
                return True

        return False

    def preserve(self, content):

        for pattern in content['transform']:
            if fnmatch.fnmatch(content['source'], pattern):
                return False

        for pattern in content['preserve']:
            if fnmatch.fnmatch(content['source'], pattern):
                return True

        return False

    def source(self, cnc, content):

        with open(f"/opt/service/cnc/{cnc['id']}/source/{content['source']}", "r") as load_file:
            return load_file.read()

    def destination(self, cnc, content, data=None):

        if data is not None:
            with open(f"/opt/service/cnc/{cnc['id']}/destination/{content['destination']}", "w") as destination_file:
                destination_file.write(data)
        else:
            with open(f"/opt/service/cnc/{cnc['id']}/destination/{content['destination']}", "r") as destination_file:
                return destination_file.read()

    def copy(self, cnc, content):
        shutil.copy(
            f"/opt/service/cnc/{cnc['id']}/source/{content['source']}",
            f"/opt/service/cnc/{cnc['id']}/destination/{content['destination']}"
        )

    def craft(self, cnc, code, change, content, values):

        if self.exclude(content):
            return

        print(content)

        cnc['content'] = content

        if os.path.isdir(f"/opt/service/cnc/{cnc['id']}/source/{content['source']}"):

            if not os.path.exists(f"/opt/service/cnc/{cnc['id']}/destination/{content['source']}"):
                os.makedirs(f"/opt/service/cnc/{cnc['id']}/destination/{content['source']}")

            for item in os.listdir(f"/opt/service/cnc/{cnc['id']}/source/{content['source']}"):
                self.craft(cnc, code, change, {
                    "source": f"{content['source']}/{item}",
                    "destination": f"{content['destination']}/{item}",
                    "exclude": content['exclude'],
                    "include": content['include'],
                    "preserve": content['preserve'],
                    "transform": content['transform']
                }, values)
            return

        if self.preserve(content):
            self.copy(cnc, content)
        else:
            self.destination(cnc, content, self.transform(self.source(cnc, content), cnc["values"]))

        del cnc['content']

    def content(self, cnc, code, change, content, values):

        content["source"] = self.transform(content["source"], values)
        content["destination"] = self.transform(content["destination"], values)

        for collection in ["exclude", "include", "preserve", "transform"]:
            content[collection] = self.transform(content.get(collection, []), values)
            if isinstance(content[collection], str):
                content[collection] = [content[collection]]

        self.craft(cnc, code, change, content, values)

    def change(self, cnc, code, change, values):

        if "github" in change:
            change["github"] = self.transform(change["github"], values)
            self.github.change(cnc, code, change["github"])

        for content, content_values in self.iterate(change["content"], values):
            self.content(cnc, code, change, content, content_values)

    def code(self, cnc, code, values):

        if "github" in code:
            code["github"] = self.transform(code["github"], values)
            self.github.clone(cnc, code, code["github"])

        for change, change_values in self.iterate(code["change"], values):
            self.change(cnc, code, change, change_values)

        if "github" in code:
            self.github.commit(cnc, code, code["github"])

    def cnc(self, cnc):

        cnc["code"] = cnc["output"]["code"]

        os.makedirs(f"/opt/service/cnc/{cnc['id']}", exist_ok=True)

        for code, code_values in self.iterate(cnc["code"], cnc["values"]):
            self.code(cnc, code, code_values)

        shutil.rmtree(f"/opt/service/cnc/{cnc['id']}")

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
