"""Tests for backup_core listing, verifying and labelling backups."""
import os
import tempfile
import unittest
from datetime import datetime

from tests.helpers import add_src_to_path, make_fake_install

add_src_to_path()
import backup_core as bc  # noqa: E402

DAY1 = datetime(2026, 10, 1, 9, 0, 0)
DAY2 = datetime(2026, 10, 2, 9, 0, 0)
DAY3 = datetime(2026, 10, 3, 9, 0, 0)


class TestListBackups(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.install = make_fake_install(self.tmp)
        self.root = os.path.join(self.tmp, "backups")
        os.makedirs(self.root)
        self.r1 = bc.create_backup(self.install, self.root, now=DAY1)
        self.r3 = bc.create_backup(self.install, self.root, now=DAY3)
        self.r2 = bc.create_backup(self.install, self.root, now=DAY2)
        self.rb = bc.create_backup(self.install, self.root, kind="before-restore", now=DAY2)

    def tearDown(self):
        self._tmp.cleanup()

    def test_order_and_kinds(self):
        items = bc.list_backups(self.root)
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].folder, self.r3.folder)
        self.assertEqual(items[-1].folder, self.r1.folder)
        self.assertEqual(items[0].created, DAY3)
        kinds = {i.folder: i.kind for i in items}
        self.assertEqual(kinds[self.rb.folder], "before-restore")
        self.assertEqual(kinds[self.r1.folder], "backup")
        self.assertTrue(all(i.manifest_ok and len(i.files) == 4 for i in items))
        self.assertEqual(items[0].source_dir, self.install)

    def test_ignores_random_and_lists_dated_without_manifest(self):
        os.makedirs(os.path.join(self.root, "notes"))
        dated = os.path.join(self.root, "2026-10-05_10-00-00")
        os.makedirs(dated)
        items = bc.list_backups(self.root)
        self.assertEqual(len(items), 5)
        self.assertNotIn("notes", [os.path.basename(i.folder) for i in items])
        info = items[0]
        self.assertEqual(info.folder, dated)
        self.assertFalse(info.manifest_ok)
        self.assertEqual(info.files, [])
        self.assertEqual(info.created, datetime(2026, 10, 5, 10, 0, 0))
        self.assertIn("details missing", bc.backup_label(info))

    def test_missing_root(self):
        self.assertEqual(bc.list_backups(os.path.join(self.tmp, "nope")), [])

    def test_verify_ok_damaged_missing(self):
        info = next(i for i in bc.list_backups(self.root) if i.folder == self.r1.folder)
        self.assertEqual(bc.verify_backup(info), (True, []))
        target = os.path.join(info.folder, "Profiles", "Profile1.cfg")
        with open(target, "r+b") as f:
            f.write(b"X")
        ok, problems = bc.verify_backup(info)
        self.assertFalse(ok)
        self.assertEqual(problems, ["Profile1.cfg in the backup is damaged "
                                    "(it doesn't match the original)."])
        self.assertEqual(bc.verify_backup(info, ["Profiles/Profile2.cfg"]), (True, []))
        os.rename(target, target + ".old")
        ok, problems = bc.verify_backup(info, ["Profiles/Profile1.cfg"])
        self.assertFalse(ok)
        self.assertEqual(problems, ["Profile1.cfg is missing from the backup."])

    def test_labels(self):
        items = {i.folder: i for i in bc.list_backups(self.root)}
        label = bc.backup_label(items[self.r3.folder])
        self.assertEqual(label, "Sat 03 Oct 2026, 9:00 AM — 4 profiles")
        safety = bc.backup_label(items[self.rb.folder])
        self.assertIn("4 profiles", safety)
        self.assertIn("safety copy", safety)


if __name__ == "__main__":
    unittest.main()
