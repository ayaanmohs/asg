"""
Test suite for the scrub controller's throttling logic.

Run with: python3 -m unittest asg.tests.test_throttle -v
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock

from asg.scrub_controller import (
    get_load_average,
    is_system_busy,
)
from asg import config


def _init_test_config():
    """Initialise config with defaults for testing."""
    config._active_config = config._deep_merge(config._DEFAULTS, {})
    config._active_config["state_dir"] = "/tmp/asg-test"


class TestLoadAverage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_test_config()

    @patch("builtins.open", mock_open(read_data="0.50 0.60 0.70 1/234 5678\n"))
    def test_normal_load(self):
        self.assertAlmostEqual(get_load_average(), 0.50)

    @patch("builtins.open", mock_open(read_data="4.25 3.10 2.80 5/456 7890\n"))
    def test_high_load(self):
        self.assertAlmostEqual(get_load_average(), 4.25)

    @patch("builtins.open", mock_open(read_data="0.00 0.01 0.05 1/100 1234\n"))
    def test_idle_system(self):
        self.assertAlmostEqual(get_load_average(), 0.00)

    @patch("builtins.open", side_effect=OSError("File not found"))
    def test_proc_unavailable(self, _mock):
        self.assertEqual(get_load_average(), 0.0)

    @patch("builtins.open", mock_open(read_data="garbage data\n"))
    def test_malformed_loadavg(self):
        self.assertEqual(get_load_average(), 0.0)


class TestSystemBusy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_test_config()

    @patch("asg.scrub_controller.get_io_utilisation")
    @patch("asg.scrub_controller.get_load_average")
    def test_idle_system_not_busy(self, mock_load, mock_io):
        mock_load.return_value = 0.5
        mock_io.return_value = {"sdc": 2.0, "sdd": 2.0}
        busy, reason = is_system_busy()
        self.assertFalse(busy)
        self.assertEqual(reason, "")

    @patch("asg.scrub_controller.get_io_utilisation")
    @patch("asg.scrub_controller.get_load_average")
    def test_high_load_triggers_busy(self, mock_load, mock_io):
        mock_load.return_value = 3.5
        mock_io.return_value = {"sdc": 5.0}
        busy, reason = is_system_busy()
        self.assertTrue(busy)
        self.assertIn("load average", reason)

    @patch("asg.scrub_controller.get_io_utilisation")
    @patch("asg.scrub_controller.get_load_average")
    def test_high_io_triggers_busy(self, mock_load, mock_io):
        mock_load.return_value = 1.0
        mock_io.return_value = {"sdc": 65.0, "sdd": 5.0}
        busy, reason = is_system_busy()
        self.assertTrue(busy)
        self.assertIn("I/O utilisation", reason)

    @patch("asg.scrub_controller.get_io_utilisation")
    @patch("asg.scrub_controller.get_load_average")
    def test_boundary_load_not_busy(self, mock_load, mock_io):
        """Load exactly at threshold should NOT trigger (strict >)."""
        mock_load.return_value = 3.0
        mock_io.return_value = {"sdc": 0.0}
        busy, _reason = is_system_busy()
        self.assertFalse(busy)

    @patch("asg.scrub_controller.get_io_utilisation")
    @patch("asg.scrub_controller.get_load_average")
    def test_boundary_io_not_busy(self, mock_load, mock_io):
        """I/O exactly at threshold should NOT trigger (strict >)."""
        mock_load.return_value = 0.5
        mock_io.return_value = {"sdc": 40.0, "sdd": 40.0}
        busy, _reason = is_system_busy()
        self.assertFalse(busy)

    @patch("asg.scrub_controller.get_io_utilisation")
    @patch("asg.scrub_controller.get_load_average")
    def test_just_above_threshold_triggers(self, mock_load, mock_io):
        mock_load.return_value = 0.5
        mock_io.return_value = {"sdc": 10.0, "sdd": 40.1}
        busy, reason = is_system_busy()
        self.assertTrue(busy)


class TestThresholdDefaults(unittest.TestCase):
    """Verify default thresholds are sensible."""

    @classmethod
    def setUpClass(cls):
        _init_test_config()

    def test_load_threshold_reasonable(self):
        cfg = config.get()
        self.assertGreaterEqual(cfg["scrub"]["load_threshold"], 1.0)
        self.assertLessEqual(cfg["scrub"]["load_threshold"], 4.0)

    def test_io_threshold_reasonable(self):
        cfg = config.get()
        self.assertGreaterEqual(cfg["scrub"]["io_threshold_percent"], 10.0)
        self.assertLessEqual(cfg["scrub"]["io_threshold_percent"], 80.0)

    def test_poll_interval_not_too_aggressive(self):
        cfg = config.get()
        self.assertGreaterEqual(cfg["scrub"]["poll_interval_seconds"], 10)

    def test_grace_period_exists(self):
        cfg = config.get()
        self.assertGreater(cfg["scrub"]["grace_period_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
