"""Tests for the basic helpers in backup_core (hashing, formatting, paths, discovery)."""
import os
import tempfile
import unittest
from datetime import datetime

from tests.helpers import add_src_to_path, make_fake_install

add_src_to_path()
import backup_core as bc  # noqa: E402


class TestFormatting(unittest.TestCase):
    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.bin")
            with open(path, "wb") as f:
                f.write(b"abc")
            self.assertEqual(
                bc.sha256_file(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_sha256_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError):
                bc.sha256_file(os.path.join(tmp, "nope"))

    def test_friendly_size(self):
        self.assertEqual(bc.friendly_size(512), "512 bytes")
        self.assertEqual(bc.friendly_size(1536), "1.5 KB")
        self.assertEqual(bc.friendly_size(3 * 1024 * 1024), "3.0 MB")

    def test_friendly_datetime(self):
        self.assertEqual(bc.friendly_datetime(datetime(2026, 10, 18, 14, 3)),
                         "Sun 18 Oct 2026, 2:03 PM")
        self.assertEqual(bc.friendly_datetime(datetime(2026, 10, 18, 11, 5)),
                         "Sun 18 Oct 2026, 11:05 AM")

    def test_folder_name_round_trip(self):
        now = datetime(2026, 10, 18, 14, 3, 22)
        name = bc.make_backup_folder_name(now)
        self.assertEqual(name, "2026-10-18_14-03-22")
        self.assertEqual(bc.parse_backup_folder_name(name), now)
        self.assertEqual(bc.parse_backup_folder_name("2026-10-18_14-03-22_2"), now)
        self.assertIsNone(bc.parse_backup_folder_name("hello"))
        self.assertIsNone(bc.parse_backup_folder_name("2026-13-45_99-99-99"))


class TestSafeRelPath(unittest.TestCase):
    def test_safe(self):
        self.assertTrue(bc.is_safe_rel_path("MSIAfterburner.cfg"))
        self.assertTrue(bc.is_safe_rel_path("Profiles/Profile1.cfg"))
        self.assertTrue(bc.is_safe_rel_path("Profiles/Profile1.CFG"))

    def test_unsafe(self):
        for bad in ["../x.cfg", "Profiles/../x.cfg", "Profiles/a/b.cfg", "Profiles/x.txt",
                    "C:/x.cfg", "Profiles\\x.cfg", "Profiles/", "Profiles/..", "", "x.cfg"]:
            self.assertFalse(bc.is_safe_rel_path(bad), bad)


class TestDiscovery(unittest.TestCase):
    def test_list_profile_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = make_fake_install(tmp)
            files = bc.list_profile_files(install, True)
            self.assertEqual(len(files), 4)
            self.assertEqual(files[-1].rel_path, "MSIAfterburner.cfg")
            rels = [f.rel_path for f in files[:-1]]
            self.assertEqual(rels, sorted(rels, key=str.lower))
            self.assertTrue(all(f.rel_path.startswith("Profiles/") for f in files[:-1]))
            self.assertTrue(all(os.path.isfile(f.abs_path) and f.size > 0 for f in files))
            self.assertEqual(len(bc.list_profile_files(install, False)), 3)

    def test_missing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(bc.list_profile_files(os.path.join(tmp, "none")), [])

    def test_valid_install_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = make_fake_install(tmp)
            self.assertTrue(bc.is_valid_install_dir(install))
            self.assertFalse(bc.is_valid_install_dir(tmp))
            self.assertFalse(bc.is_valid_install_dir(None))
            self.assertFalse(bc.is_valid_install_dir(""))


class TestWritable(unittest.TestCase):
    def test_writable(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(bc.check_folder_writable(tmp), (True, ""))
            self.assertEqual(os.listdir(tmp), [])

    def test_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "nope")
            ok, msg = bc.check_folder_writable(missing)
            self.assertFalse(ok)
            self.assertIn("can't reach", msg)
            self.assertFalse(os.path.exists(missing))

    def test_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")
            ok, msg = bc.check_folder_writable(path)
            self.assertFalse(ok)
            self.assertIn("file, not a folder", msg)


if __name__ == "__main__":
    unittest.main()
