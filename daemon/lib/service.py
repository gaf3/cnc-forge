"""
Main module for daemon
"""

import os
import json
import time
import traceback
import subprocess

import redis
import jinja2

import cnc
import github

class Daemon:
    """
    Main class for daemon
    """

    def __init__(self):

        self.sleep = int(os.environ['SLEEP'])

        with open("/opt/service/secret/redis.json", "r") as redis_file:
            self.redis = redis.Redis(charset="utf-8", decode_responses=True, **json.loads(redis_file.read()))

        with open("/opt/service/secret/github.json", "r") as github_file:
            self.github = github.GitHub(**json.loads(github_file.read()))

        self.cnc = cnc.CnC(self)

        subprocess.check_output("mkdir -p /root/.ssh", shell=True)
        subprocess.check_output("cp /opt/service/secret/github.key /root/.ssh/", shell=True)
        subprocess.check_output("chmod 600 /root/.ssh/github.key", shell=True)
        subprocess.check_output("cp /opt/service/secret/.sshconfig /root/.ssh/config", shell=True)
        subprocess.check_output("cp /opt/service/secret/.gitconfig /root/.gitconfig", shell=True)

        self.env = jinja2.Environment(keep_trailing_newline=True)

    def process(self):
        """
        Processes all the routines for reminding
        """

        for key in self.redis.keys("/cnc/*"):

            data = json.loads(self.redis.get(key))

            if data["status"] not in ["Created", "Retry"]:
                continue

            try:
                self.cnc.process(data)
            except Exception as exception:
                data["status"] = "Error"
                data["error"] = str(exception)
                data["traceback"] = traceback.format_exc()

            self.redis.set(key, json.dumps(data), ex=24*60*60)

    def run(self):
        """
        Runs the daemon
        """

        while True:
            self.process()
            time.sleep(self.sleep)
