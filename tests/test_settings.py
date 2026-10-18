"""Tests for settings.py: settings file, log file, resource paths."""
import os
import shutil
import tempfile
import unittest

from tests import helpers

helpers.add_src_to_path()
import settings  # noqa: E402


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.old_env = os.environ.get("ABPB_SETTINGS_DIR")
        os.environ["ABPB_SETTINGS_DIR"] = self.tmp

    def tearDown(self) -> None:
        if self.old_env is None:
            os.environ.pop("ABPB_SETTINGS_DIR", None)
        else:
            os.environ["ABPB_SETTINGS_DIR"] = self.old_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_without_file_gives_defaults(self) -> None:
        self.assertEqual(settings.load_settings(), settings.Settings())

    def test_save_then_load(self) -> None:
        s = settings.Settings(r"C:\Example\MSI Afterburner", True, r"\\NAS\share\Backups", False)
        self.assertTrue(settings.save_settings(s))
        self.assertEqual(settings.load_settings(), s)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "settings.json.tmp")))

    def test_corrupt_json_gives_defaults(self) -> None:
        with open(os.path.join(self.tmp, "settings.json"), "w", encoding="utf-8") as f:
            f.write("{ not json")
        self.assertEqual(settings.load_settings(), settings.Settings())

    def test_wrong_types_and_unknown_keys(self) -> None:
        with open(os.path.join(self.tmp, "settings.json"), "w", encoding="utf-8") as f:
            f.write('{"install_dir": 5, "install_confirmed": "yes", "include_main_cfg": false,'
                    ' "backup_root": "D:\\\\Backups", "extra": 1}')
        s = settings.load_settings()
        self.assertIsNone(s.install_dir)
        self.assertFalse(s.install_confirmed)
        self.assertFalse(s.include_main_cfg)
        self.assertEqual(s.backup_root, "D:\\Backups")

    def test_log_writes_line(self) -> None:
        settings.log("WARN", "hello world")
        with open(settings.log_path(), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("WARN hello world", text)

    def test_log_rotates_when_large(self) -> None:
        with open(settings.log_path(), "w", encoding="utf-8") as f:
            f.write("x" * 1_000_001)
        settings.log("INFO", "after rotation")
        old = os.path.join(self.tmp, "log.old.txt")
        self.assertTrue(os.path.exists(old))
        self.assertGreater(os.path.getsize(old), 1_000_000)
        with open(settings.log_path(), encoding="utf-8") as f:
            self.assertIn("after rotation", f.read())
        self.assertLess(os.path.getsize(settings.log_path()), 1000)

    def test_resource_path(self) -> None:
        self.assertTrue(settings.resource_path("docs/QUICKSTART.md").endswith(
            os.path.join("docs", "QUICKSTART.md")))

    def test_read_help_text_never_empty(self) -> None:
        self.assertTrue(settings.read_help_text())


if __name__ == "__main__":
    unittest.main()
