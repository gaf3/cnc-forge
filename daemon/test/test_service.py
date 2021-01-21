import unittest
import unittest.mock
import klotio_unittest

import os
import json

import service


class TestService(klotio_unittest.TestCase):

    @unittest.mock.patch.dict(os.environ, {
        "CHORE_API": "http://toast.com",
        "SLEEP": "0.7"
    })
    @unittest.mock.patch("klotio.logger", klotio_unittest.MockLogger)
    def setUp(self):

        self.daemon = service.Daemon()

    @unittest.mock.patch.dict(os.environ, {
        "CHORE_API": "http://toast.com",
        "SLEEP": "0.7"
    })
    @unittest.mock.patch("klotio.logger", klotio_unittest.MockLogger)
    def test___init___(self):

        daemon = service.Daemon()

        self.assertEqual(daemon.chore_api, "http://toast.com")
        self.assertEqual(daemon.sleep, 0.7)

        self.assertEqual(daemon.logger.name, "nandy-io-chore-daemon")

        self.assertLogged(daemon.logger, "debug", "init", extra={
            "init": {
                "sleep": 0.7,
                "chore_api": "http://toast.com"
            }
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_expire(self):

        self.assertTrue(self.daemon.expire({
            "expires": 5,
            "start": 1
        }))

        self.assertFalse(self.daemon.expire({
            "expires": 6,
            "start": 1
        }))

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_remind(self):

        self.assertFalse(self.daemon.remind({
            "delay": 7,
            "start": 1
        }))

        self.assertFalse(self.daemon.remind({
            "delay": 6,
            "start": 1,
            "paused": True
        }))

        self.assertTrue(self.daemon.remind({
            "delay": 6,
            "start": 1,
            "paused": False,
            "interval": 2,
            "notified": 4
        }))

        self.assertFalse(self.daemon.remind({
            "delay": 6,
            "start": 1,
            "paused": False,
            "interval": 2,
            "notified": 5
        }))

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("requests.patch")
    def test_tasks(self, mock_patch):

        routine = {
            "id": 1,
            "data": {
                "text": "hey",
                "language": "cursing",
                "tasks": [
                    {
                        "id": 0,
                        "start": 0,
                        "delay": 6,
                        "start": 1,
                        "paused": False,
                        "interval": 2,
                        "notified": 4
                    }
                ]
            }
        }

        self.daemon.tasks(routine)
        mock_patch.assert_has_calls([
            unittest.mock.call("http://toast.com/routine/1/task/0/remind"),
            unittest.mock.call().raise_for_status()
        ])

        self.assertLogged(self.daemon.logger, "info", "task", extra={
            "task": {
                "id": 0,
                "start": 0,
                "delay": 6,
                "start": 1,
                "paused": False,
                "interval": 2,
                "notified": 4
            }
        })

        self.assertLogged(self.daemon.logger, "info", "remind")

        routine["data"]["tasks"][0]["notified"] = 7
        self.daemon.tasks(routine)
        mock_patch.assert_called_once()

        routine["data"]["tasks"][0]["notified"] = 4
        routine["data"]["tasks"][0]["end"] = 0
        self.daemon.tasks(routine)
        mock_patch.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("requests.patch")
    def test_routine(self, mock_patch):

        routine =  {
            "id": 1,
            "data": {
                "start": 0,
                "expires": 6
            }
        }

        self.daemon.routine(routine)

        mock_patch.assert_has_calls([
            unittest.mock.call("http://toast.com/routine/1/expire"),
            unittest.mock.call().raise_for_status(),
        ])

        self.assertLogged(self.daemon.logger, "info", "routine", extra={
            "routine": {
                "id": 1,
                "data": {
                    "start": 0,
                    "expires": 6
                }
            }
        })

        self.assertLogged(self.daemon.logger, "info", "expire")

        routine =  {
            "id": 1,
            "data": {
                "start": 0,
                "delay": 6,
                "start": 1,
                "paused": False,
                "interval": 2,
                "notified": 4,
                "text": "hey",
                "language": "cursing",
                "tasks": [
                    {
                        "id": 0,
                        "start": 0,
                        "delay": 6,
                        "start": 1,
                        "paused": False,
                        "interval": 2,
                        "notified": 4
                    }
                ]
            }
        }

        mock_patch.reset_mock()

        self.daemon.routine(routine)

        mock_patch.assert_has_calls([
            unittest.mock.call("http://toast.com/routine/1/remind"),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call("http://toast.com/routine/1/task/0/remind"),
            unittest.mock.call().raise_for_status()
        ])

        self.assertLogged(self.daemon.logger, "info", "expire")

        routine["data"]["notified"] = 7
        routine["data"]["tasks"][0]["notified"] = 7

        self.daemon.routine(routine)
        self.assertEqual(mock_patch.call_count, 2)

    @unittest.mock.patch("requests.get")
    @unittest.mock.patch("service.Daemon.routine")
    @unittest.mock.patch("traceback.format_exc")
    @unittest.mock.patch('builtins.print')
    def test_process(self, mock_print, mock_traceback, mock_routine, mock_get):

        mock_get.return_value.json.return_value = {
            "routines": ["hey"]
        }

        mock_routine.side_effect= [Exception("whoops")]
        mock_traceback.return_value = "spirograph"

        self.daemon.process()

        mock_get.assert_called_with("http://toast.com/routine?status=opened")

        mock_routine.assert_called_once_with("hey")

        mock_print.assert_has_calls([
            unittest.mock.call("whoops"),
            unittest.mock.call("spirograph")
        ])

    @unittest.mock.patch("requests.get")
    @unittest.mock.patch("service.time.sleep")
    def test_run(self, mock_sleep, mock_get):

        mock_get.return_value.json.return_value = {
            "routines": []
        }

        mock_sleep.side_effect = [Exception("adaisy")]

        self.assertRaisesRegex(Exception, "adaisy", self.daemon.run)

        mock_sleep.assert_called_with(0.7)
