"""
Main module for daemon
"""

import os
import json
import time
import traceback

import redis

import cnc
import github

class Daemon:
    """
    Main class for daemon
    """

    def __init__(self):

        self.sleep = int(os.environ['SLEEP'])

        self.redis = redis.Redis(host="redis.cnc-forge", charset="utf-8", decode_responses=True)

        github.GitHub.config()

    def process(self):
        """
        Processes all the routines for reminding
        """

        for key in self.redis.keys("/cnc/*"):

            data = json.loads(self.redis.get(key))

            if data["status"] not in ["Created", "Retry"]:
                continue

            try:
                cnc.CnC(data).process()
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
