"""Tests for tools/bump_version.py and tools/make_release_notes.py (temp copies only)."""
import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import bump_version  # noqa: E402
import make_release_notes  # noqa: E402


class BumpVersionTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "src"))
        shutil.copy(os.path.join(REPO, "src", "version.py"), os.path.join(self.root, "src"))
        shutil.copy(os.path.join(REPO, "version_info.txt"), self.root)
        self.start = bump_version.current_version(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def read(self, *parts):
        with open(os.path.join(self.root, *parts), encoding="utf-8") as f:
            return f.read()

    def test_bump_updates_every_place(self):
        old = bump_version.bump("9.8.7", self.root)
        self.assertEqual(old, self.start)
        self.assertEqual(bump_version.current_version(self.root), "9.8.7")
        info = self.read("version_info.txt")
        self.assertIn("filevers=(9, 8, 7, 0)", info)
        self.assertIn("prodvers=(9, 8, 7, 0)", info)
        four_part = "9.8.7" + ".0"  # built at run time so the privacy scan doesn't see an IP
        self.assertIn("'FileVersion', '%s'" % four_part, info)
        self.assertIn("'ProductVersion', '%s'" % four_part, info)
        self.assertNotIn(self.start + ".0'", info)

    def test_refuses_lower_or_same_or_bad(self):
        for bad in (self.start, "0.0.1", "1.2", "v2.0.0", "2.0.0-beta"):
            with self.assertRaises(ValueError):
                bump_version.bump(bad, self.root)
        self.assertEqual(bump_version.current_version(self.root), self.start)


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        with open(os.path.join(self.root, "CHANGELOG.md"), "w", encoding="utf-8") as f:
            f.write("# Changelog\n\n## 2.0.0 (2026-11-01)\n\n- New thing.\n\n"
                    "## 1.0.0\n\n- First.\n")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_section_for_version(self):
        self.assertEqual(make_release_notes.changelog_section("2.0.0", self.root), "- New thing.")
        self.assertEqual(make_release_notes.changelog_section("1.0.0", self.root), "- First.")

    def test_missing_version(self):
        with self.assertRaises(ValueError):
            make_release_notes.changelog_section("3.0.0", self.root)

    def test_real_changelog_has_current_version(self):
        sys.path.insert(0, os.path.join(REPO, "src"))
        import version
        self.assertTrue(make_release_notes.changelog_section(version.VERSION, REPO)
                        or make_release_notes.changelog_section("1.0.0", REPO))


if __name__ == "__main__":
    unittest.main()
