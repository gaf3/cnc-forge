import unittest
import unittest.mock

import os
import json
import fnmatch

import service

class MockRedis:

    def __init__(self, host, **kwargs):

        self.host = host

        self.data = {}
        self.expires = {}
        self.messages = []

        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __str__(self):

        return f"MockRedis<host={self.host},port={self.port}>"

    def get(self, key):

        return self.data.get(key)

    def set(self, key, value, ex=None):

        self.data[key] = value
        self.expires[key] = ex

    def keys(self, pattern):

        for key in sorted(self.data.keys()):
            if fnmatch.fnmatch(key, pattern):
                yield key

class TestService(unittest.TestCase):

    @unittest.mock.patch.dict(os.environ, {
        "SLEEP": "7"
    })
    @unittest.mock.patch("redis.Redis", MockRedis)
    @unittest.mock.patch("github.GitHub.config", unittest.mock.MagicMock)
    def setUp(self):

        self.daemon = service.Daemon()

    @unittest.mock.patch.dict(os.environ, {
        "SLEEP": "7"
    })

    @unittest.mock.patch("redis.Redis", MockRedis)
    @unittest.mock.patch("github.GitHub.config")
    def test___init___(self, mock_github):

        daemon = service.Daemon()

        self.assertEqual(daemon.sleep, 7)

        self.assertEqual(daemon.redis.host, "redis.cnc-forge")

        mock_github.assert_called_once_with()

    @unittest.mock.patch("cnc.CnC.process")
    @unittest.mock.patch("traceback.format_exc")
    def test_process(self, mock_traceback, mock_process):

        self.daemon.redis.set("/cnc/music", json.dumps({"status": "Created"}))
        self.daemon.redis.set("/cnc/factory", json.dumps({"status": "Retry"}))
        self.daemon.redis.set("/cnc/sing", json.dumps({"status": "Nope"}))

        mock_process.side_effect= Exception("whoops")
        mock_traceback.return_value = "adaisy"

        self.daemon.process()

        self.assertEqual(json.loads(self.daemon.redis.get("/cnc/music")), {
            "status": "Error",
            "error": "whoops",
            "traceback": "adaisy"
        })

        self.assertEqual(json.loads(self.daemon.redis.get("/cnc/factory")), {
            "status": "Error",
            "error": "whoops",
            "traceback": "adaisy"
        })

        self.assertEqual(json.loads(self.daemon.redis.get("/cnc/sing")), {
            "status": "Nope"
        })

    @unittest.mock.patch("service.time.sleep")
    def test_run(self, mock_sleep):

        mock_sleep.side_effect = [Exception("whoops")]

        self.assertRaisesRegex(Exception, "whoops", self.daemon.run)

        mock_sleep.assert_called_with(7)
