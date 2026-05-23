import importlib
import os
import sys
import unittest
from unittest.mock import patch


class AppSchedulerStartupTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("app", None)
        os.environ.pop("FLASK_DEBUG", None)
        os.environ.pop("WERKZEUG_RUN_MAIN", None)

    def test_debug_reloader_parent_does_not_start_scheduler(self):
        os.environ["FLASK_DEBUG"] = "1"
        os.environ.pop("WERKZEUG_RUN_MAIN", None)
        sys.modules.pop("app", None)

        with patch("scheduler.start_scheduler") as start_scheduler:
            importlib.import_module("app")

        start_scheduler.assert_not_called()

    def test_scheduler_starts_once_in_serving_process(self):
        os.environ["FLASK_DEBUG"] = "1"
        os.environ["WERKZEUG_RUN_MAIN"] = "true"
        sys.modules.pop("app", None)

        with patch("scheduler.start_scheduler") as start_scheduler:
            app_module = importlib.import_module("app")
            app_module._start_scheduler_once()

        start_scheduler.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
