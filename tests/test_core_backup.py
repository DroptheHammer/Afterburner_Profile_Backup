"""Tests for backup_core backup functions (manifest, verified copy, create_backup)."""
import json
import os
import tempfile
import unittest
from datetime import datetime

from tests.helpers import add_src_to_path, make_fake_install

add_src_to_path()
import backup_core as bc  # noqa: E402

NOW = datetime(2026, 10, 18, 14, 3, 22)


class TestCreateBackup(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.install = make_fake_install(self.tmp)
        self.root = os.path.join(self.tmp, "backups")
        os.makedirs(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_backup_ok(self):
        res = bc.create_backup(self.install, self.root, now=NOW)
        self.assertTrue(res.ok, res.message)
        self.assertEqual(res.count, 4)
        self.assertIsNotNone(bc.parse_backup_folder_name(os.path.basename(res.folder)))
        manifest = bc.read_manifest(res.folder)
        self.assertEqual(manifest["kind"], "backup")
        self.assertEqual(manifest["created_local"], "2026-10-18T14:03:22")
        self.assertEqual(len(manifest["files"]), 4)
        for entry in manifest["files"]:
            path = os.path.join(res.folder, *entry["rel_path"].split("/"))
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(entry["sha256"], bc.sha256_file(path))
            self.assertEqual(entry["size"], os.path.getsize(path))
        self.assertTrue(os.path.isfile(os.path.join(res.folder, "Profiles", "Profile1.cfg")))
        self.assertIn("Verified OK", res.message)

    def test_same_second_gets_suffix(self):
        first = bc.create_backup(self.install, self.root, now=NOW)
        second = bc.create_backup(self.install, self.root, now=NOW)
        self.assertTrue(second.ok)
        self.assertNotEqual(first.folder, second.folder)
        self.assertTrue(second.folder.endswith("_2"))

    def test_dry_run(self):
        res = bc.create_backup(self.install, self.root, dry_run=True, now=NOW)
        self.assertTrue(res.ok)
        self.assertEqual(res.count, 4)
        self.assertFalse(os.path.exists(res.folder))
        self.assertTrue(res.message.startswith("Test run"))
        self.assertEqual(os.listdir(self.root), [])

    def test_before_restore_folder(self):
        res = bc.create_backup(self.install, self.root, kind="before-restore", now=NOW)
        self.assertTrue(res.ok, res.message)
        self.assertEqual(os.path.dirname(res.folder),
                         os.path.join(self.root, "before-restore"))
        self.assertEqual(bc.read_manifest(res.folder)["kind"], "before-restore")

    def test_unreachable_root(self):
        res = bc.create_backup(self.install, os.path.join(self.tmp, "nope"), now=NOW)
        self.assertFalse(res.ok)
        self.assertIn("can't reach", res.message)

    def test_no_profiles(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(os.path.join(empty, "Profiles"))
        res = bc.create_backup(empty, self.root, include_main_cfg=False, now=NOW)
        self.assertFalse(res.ok)
        self.assertIn("didn't find", res.message)

    def test_originals_unchanged(self):
        before = {f.rel_path: bc.sha256_file(f.abs_path)
                  for f in bc.list_profile_files(self.install)}
        bc.create_backup(self.install, self.root, now=NOW)
        after = {f.rel_path: bc.sha256_file(f.abs_path)
                 for f in bc.list_profile_files(self.install)}
        self.assertEqual(before, after)


class TestHelpers(unittest.TestCase):
    def test_read_manifest_drops_unsafe(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = {"files": [
                {"rel_path": "../evil.cfg", "size": 1, "sha256": "x"},
                {"rel_path": "Profiles/ok.cfg", "size": 1, "sha256": "y"}]}
            with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(data, f)
            files = bc.read_manifest(tmp)["files"]
            self.assertEqual([e["rel_path"] for e in files], ["Profiles/ok.cfg"])

    def test_read_manifest_bad(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(bc.read_manifest(tmp))
            with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertIsNone(bc.read_manifest(tmp))

    def test_copy_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "a.cfg")
            with open(src, "wb") as f:
                f.write(b"hello")
            dst = os.path.join(tmp, "sub", "a.cfg")
            size, digest = bc.copy_verified(src, dst)
            self.assertEqual(size, 5)
            self.assertEqual(digest, bc.sha256_file(dst))
            self.assertFalse(os.path.exists(dst + bc.TEMP_SUFFIX))


if __name__ == "__main__":
    unittest.main()
