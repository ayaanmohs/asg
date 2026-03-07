"""
Test suite for the pool validator.

Run with: python3 -m unittest asg.tests.test_pool_validator -v
"""

import unittest
from unittest.mock import patch, MagicMock

from asg.pool_validator import (
    validate_pool,
    PoolValidationError,
    _get_mounted_uuid,
)
from asg import config


def _init_test_config(**overrides):
    base = config._deep_merge(config._DEFAULTS, overrides)
    base["state_dir"] = "/tmp/asg-test"
    config._active_config = base


class TestPoolValidator(unittest.TestCase):

    @patch("asg.pool_validator._get_mounted_uuid")
    @patch("asg.pool_validator._is_mountpoint")
    @patch("os.path.isdir")
    def test_valid_pool_no_uuid_pin(self, mock_isdir, mock_mount, mock_uuid):
        """With no UUID pinned, any valid BTRFS mount passes."""
        _init_test_config()
        mock_isdir.return_value = True
        mock_mount.return_value = True
        mock_uuid.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        self.assertTrue(validate_pool())

    @patch("asg.pool_validator._get_mounted_uuid")
    @patch("asg.pool_validator._is_mountpoint")
    @patch("os.path.isdir")
    def test_valid_pool_with_uuid_pin(self, mock_isdir, mock_mount, mock_uuid):
        _init_test_config(pool={"mount": "/mnt/test", "uuid": "abc-123"})
        mock_isdir.return_value = True
        mock_mount.return_value = True
        mock_uuid.return_value = "abc-123"
        self.assertTrue(validate_pool())

    @patch("os.path.isdir")
    def test_missing_mount_dir(self, mock_isdir):
        _init_test_config()
        mock_isdir.return_value = False
        with self.assertRaises(PoolValidationError) as ctx:
            validate_pool()
        self.assertIn("does not exist", str(ctx.exception))

    @patch("asg.pool_validator._is_mountpoint")
    @patch("os.path.isdir")
    def test_not_mounted(self, mock_isdir, mock_mount):
        _init_test_config()
        mock_isdir.return_value = True
        mock_mount.return_value = False
        with self.assertRaises(PoolValidationError) as ctx:
            validate_pool()
        self.assertIn("not an active mount", str(ctx.exception))

    @patch("asg.pool_validator._get_mounted_uuid")
    @patch("asg.pool_validator._is_mountpoint")
    @patch("os.path.isdir")
    def test_uuid_mismatch(self, mock_isdir, mock_mount, mock_uuid):
        _init_test_config(pool={"mount": "/mnt/test", "uuid": "expected-uuid"})
        mock_isdir.return_value = True
        mock_mount.return_value = True
        mock_uuid.return_value = "wrong-uuid"
        with self.assertRaises(PoolValidationError) as ctx:
            validate_pool()
        self.assertIn("UUID mismatch", str(ctx.exception))

    @patch("asg.pool_validator._get_mounted_uuid")
    @patch("asg.pool_validator._is_mountpoint")
    @patch("os.path.isdir")
    def test_uuid_unavailable(self, mock_isdir, mock_mount, mock_uuid):
        _init_test_config()
        mock_isdir.return_value = True
        mock_mount.return_value = True
        mock_uuid.return_value = None
        with self.assertRaises(PoolValidationError) as ctx:
            validate_pool()
        self.assertIn("Could not determine", str(ctx.exception))

    @patch("asg.pool_validator._get_mounted_uuid")
    @patch("asg.pool_validator._is_mountpoint")
    @patch("os.path.isdir")
    def test_quiet_mode_returns_false(self, mock_isdir, mock_mount, mock_uuid):
        _init_test_config(pool={"mount": "/mnt/test", "uuid": "expected"})
        mock_isdir.return_value = True
        mock_mount.return_value = True
        mock_uuid.return_value = "wrong"
        self.assertFalse(validate_pool(quiet=True))


class TestUUIDParsing(unittest.TestCase):

    @patch("subprocess.run")
    def test_parses_uuid_correctly(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Label: 'MY_POOL'  uuid: abcd-1234-efgh-5678\n",
        )
        uuid = _get_mounted_uuid("/mnt/test")
        self.assertEqual(uuid, "abcd-1234-efgh-5678")

    @patch("subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        uuid = _get_mounted_uuid("/mnt/test")
        self.assertIsNone(uuid)


if __name__ == "__main__":
    unittest.main()
