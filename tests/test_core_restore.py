"""Tests for backup_core restore functions."""
import os
import shutil
import tempfile
import unittest
from datetime import datetime

from tests import helpers

helpers.add_src_to_path()
import backup_core as bc  # noqa: E402

P1, P2 = "Profiles/Profile1.cfg", "Profiles/Profile2.cfg"


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = helpers.make_fake_install(self.tmp)
        self.root = os.path.join(self.tmp, "backups")
        os.makedirs(self.root)
        res = bc.create_backup(self.install, self.root, now=datetime(2026, 1, 1, 10, 0, 0))
        self.assertTrue(res.ok)
        self.info = bc.list_backups(self.root)[0]
        self.p1 = bc.target_path_for(self.install, P1)
        self.p2 = bc.target_path_for(self.install, P2)
        self.orig1 = read(self.p1)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def restore(self, paths, **kw):
        return bc.restore_files(self.info, paths, self.install, self.root,
                                now=datetime(2026, 1, 2, 9, 0, 0), **kw)

    def test_restore_one(self):
        write(self.p1, "changed1")
        write(self.p2, "changed2")
        res = self.restore([P1])
        self.assertTrue(res.ok, res.message)
        self.assertEqual(res.message, "Restored 1 profile. Verified OK. "
                                      "Please open Afterburner again.")
        self.assertEqual(read(self.p1), self.orig1)
        self.assertEqual(read(self.p2), "changed2")
        self.assertIn("Replaced " + P1, res.details)
        self.assertTrue(res.safety_folder and os.path.isdir(res.safety_folder))
        self.assertEqual(read(os.path.join(res.safety_folder, "Profiles", "Profile1.cfg")),
                         "changed1")

    def test_restore_all(self):
        for rec in self.info.files:
            write(bc.target_path_for(self.install, rec.rel_path), "x")
        res = self.restore([r.rel_path for r in self.info.files])
        self.assertTrue(res.ok, res.message)
        for rec in self.info.files:
            self.assertEqual(bc.sha256_file(bc.target_path_for(self.install, rec.rel_path)),
                             rec.sha256)

    def test_dry_run(self):
        write(self.p1, "changed1")
        os.remove(self.p2)
        res = self.restore([P1, P2], dry_run=True)
        self.assertTrue(res.ok)
        self.assertTrue(res.dry_run)
        self.assertIn("Would replace " + P1, res.details)
        self.assertIn("Would add " + P2, res.details)
        self.assertEqual(read(self.p1), "changed1")
        self.assertFalse(os.path.exists(self.p2))
        self.assertFalse(os.path.exists(os.path.join(self.root, bc.BEFORE_RESTORE_DIR_NAME)))

    def test_add_deleted_file(self):
        os.remove(self.p2)
        res = self.restore([P2])
        self.assertTrue(res.ok, res.message)
        self.assertTrue(os.path.isfile(self.p2))
        self.assertIn("Added " + P2, res.details)

    def test_empty_selection(self):
        res = self.restore([])
        self.assertFalse(res.ok)
        self.assertIn("pick at least one", res.message)

    def test_not_in_backup(self):
        self.assertFalse(self.restore(["Profiles/Nope.cfg"]).ok)
        self.assertFalse(self.restore(["../x.cfg"]).ok)

    def test_damaged_backup(self):
        write(self.p1, "changed1")
        write(os.path.join(self.info.folder, "Profiles", "Profile1.cfg"), "damaged")
        res = self.restore([P1])
        self.assertFalse(res.ok)
        self.assertIn("can't be used safely", res.message)
        self.assertEqual(read(self.p1), "changed1")
        self.assertFalse(os.path.exists(os.path.join(self.root, bc.BEFORE_RESTORE_DIR_NAME)))

    def test_target_path_unsafe(self):
        with self.assertRaises(ValueError):
            bc.target_path_for(self.install, "../x.cfg")

    def test_unwritable_install(self):
        res = bc.restore_files(self.info, [P1], os.path.join(self.tmp, "missing"), self.root)
        self.assertFalse(res.ok)
        self.assertIn("administrator permission", res.message)


if __name__ == "__main__":
    unittest.main()
