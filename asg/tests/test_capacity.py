"""
Test suite for the capacity engine's free-space calculations.

Run with: python3 -m unittest asg.tests.test_capacity -v
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from asg.capacity_engine import (
    _parse_size,
    calculate_real_free_space,
    check_metadata_concentration,
    predict_days_to_full,
)
from asg import config


def _init_test_config():
    config._active_config = config._deep_merge(config._DEFAULTS, {})
    config._active_config["state_dir"] = "/tmp/asg-test"


class TestParseSize(unittest.TestCase):

    def test_gib(self):
        self.assertAlmostEqual(_parse_size("103.00GiB"), 103.0, places=1)

    def test_tib(self):
        self.assertAlmostEqual(_parse_size("1.82TiB"), 1.82 * 1024, places=0)

    def test_mib(self):
        self.assertAlmostEqual(_parse_size("502.98MiB"), 502.98 / 1024, places=2)

    def test_kib(self):
        self.assertAlmostEqual(_parse_size("16.00KiB"), 16.0 / (1024 * 1024), places=6)

    def test_bytes(self):
        self.assertAlmostEqual(_parse_size("0.00B"), 0.0)

    def test_dash(self):
        self.assertEqual(_parse_size("-"), 0.0)

    def test_empty(self):
        self.assertEqual(_parse_size(""), 0.0)


class TestRealFreeSpace(unittest.TestCase):

    def _make_usage(self, devices, data_used=100.0, meta_used=0.5):
        per_device = {}
        for path, total in devices.items():
            per_device[path] = {
                "data_gib": 0, "metadata_gib": 0, "system_gib": 0,
                "unallocated_gib": total, "total_gib": total,
            }
        return {
            "per_device": per_device,
            "data_chunks": {"used_gib": data_used, "total_gib": data_used + 5},
            "metadata_chunks": {"used_gib": meta_used, "total_gib": 1.0},
        }

    def test_four_mismatched_drives(self):
        """2TB + 1TB + 1TB + 4TB pool."""
        usage = self._make_usage({
            "/dev/sda": 1862.0,
            "/dev/sdb": 931.51,
            "/dev/sdc": 931.51,
            "/dev/sdd": 3727.0,
        }, data_used=100.46, meta_used=0.49)

        result = calculate_real_free_space(usage)
        self.assertAlmostEqual(result["usable_ceiling_gib"], 3726.01, delta=1.0)
        self.assertGreater(result["real_free_gib"], 3600.0)

    def test_symmetric_drives(self):
        usage = self._make_usage({
            "/dev/sda": 1000.0,
            "/dev/sdb": 1000.0,
        }, data_used=200.0, meta_used=0.0)

        result = calculate_real_free_space(usage)
        self.assertAlmostEqual(result["usable_ceiling_gib"], 1000.0)
        self.assertAlmostEqual(result["real_free_gib"], 800.0)

    def test_extreme_mismatch(self):
        """10TB + 1TB: usable = 1TB (large drive mostly wasted)."""
        usage = self._make_usage({
            "/dev/sda": 10240.0,
            "/dev/sdb": 1024.0,
        }, data_used=500.0, meta_used=0.0)

        result = calculate_real_free_space(usage)
        self.assertAlmostEqual(result["usable_ceiling_gib"], 1024.0)

    def test_three_drives(self):
        """3x 2TB drives."""
        usage = self._make_usage({
            "/dev/sda": 2000.0,
            "/dev/sdb": 2000.0,
            "/dev/sdc": 2000.0,
        }, data_used=100.0, meta_used=0.0)

        result = calculate_real_free_space(usage)
        self.assertAlmostEqual(result["usable_ceiling_gib"], 3000.0)

    def test_empty_pool(self):
        usage = self._make_usage({
            "/dev/sda": 1000.0,
            "/dev/sdb": 1000.0,
        }, data_used=0.0, meta_used=0.0)

        result = calculate_real_free_space(usage)
        self.assertAlmostEqual(result["real_free_gib"], 1000.0)

    def test_no_devices(self):
        result = calculate_real_free_space({"per_device": {}})
        self.assertEqual(result["usable_ceiling_gib"], 0)


class TestMetadataConcentration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_test_config()

    def test_concentrated_metadata_warns(self):
        usage = {
            "metadata_device_count": 2,
            "per_device": {
                "/dev/sda": {"metadata_gib": 0.0},
                "/dev/sdb": {"metadata_gib": 1.0},
                "/dev/sdc": {"metadata_gib": 1.0},
                "/dev/sdd": {"metadata_gib": 0.0},
            },
        }
        warnings = check_metadata_concentration(usage)
        self.assertGreater(len(warnings), 0)
        self.assertIn("concentrated", warnings[0].lower())

    def test_distributed_metadata_no_warning(self):
        usage = {
            "metadata_device_count": 3,
            "per_device": {
                "/dev/sda": {"metadata_gib": 0.5},
                "/dev/sdb": {"metadata_gib": 0.5},
                "/dev/sdc": {"metadata_gib": 0.5},
                "/dev/sdd": {"metadata_gib": 0.0},
            },
        }
        warnings = check_metadata_concentration(usage)
        meta_warnings = [w for w in warnings if "metadata" in w.lower()]
        self.assertEqual(len(meta_warnings), 0)


class TestDaysToFull(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_test_config()

    @patch("asg.capacity_engine._load_history")
    def test_insufficient_data(self, mock_history):
        mock_history.return_value = [
            {"timestamp": "2026-03-01T00:00:00", "total_used_gib": 100}
        ] * 5
        result = predict_days_to_full({"real_free_gib": 3000})
        self.assertIsNone(result)

    @patch("asg.capacity_engine._load_history")
    def test_steady_growth(self, mock_history):
        """10 GiB/day growth with 100 GiB free = ~10 days."""
        base = datetime(2026, 2, 1)
        history = [
            {"timestamp": (base + timedelta(days=i)).isoformat(), "total_used_gib": 100.0 + (i * 10.0)}
            for i in range(10)
        ]
        mock_history.return_value = history
        result = predict_days_to_full({"real_free_gib": 100.0})
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 10, delta=1)

    @patch("asg.capacity_engine._load_history")
    def test_no_growth(self, mock_history):
        base = datetime(2026, 2, 1)
        history = [
            {"timestamp": (base + timedelta(days=i)).isoformat(), "total_used_gib": 100.0}
            for i in range(10)
        ]
        mock_history.return_value = history
        result = predict_days_to_full({"real_free_gib": 3000.0})
        self.assertIsNone(result)

    @patch("asg.capacity_engine._load_history")
    def test_shrinking_usage(self, mock_history):
        base = datetime(2026, 2, 1)
        history = [
            {"timestamp": (base + timedelta(days=i)).isoformat(), "total_used_gib": 200.0 - (i * 5.0)}
            for i in range(10)
        ]
        mock_history.return_value = history
        result = predict_days_to_full({"real_free_gib": 3000.0})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
