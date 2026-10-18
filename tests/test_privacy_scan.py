"""Tests for tools/privacy_scan.py. Test data is built at run time so the repo scan stays clean."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import privacy_scan  # noqa: E402

BS = "\\"


class PrivacyScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        env = mock.patch.dict(os.environ, {"USERNAME": "zzfakeuser", "COMPUTERNAME": "ZZFAKEPC"})
        env.start()
        self.addCleanup(env.stop)

    def write(self, name: str, text: str) -> None:
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            f.write(text)

    def run_main(self) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return privacy_scan.main(["privacy_scan.py", self.root])

    def test_bad_file_three_findings(self) -> None:
        self.write("bad.txt", "mail someone" + "@example.org\nip 192." + "168.1.20\n"
                   + "C:" + BS + "Users" + BS + "alice" + BS + "x\n")
        self.assertEqual(len(privacy_scan.scan(self.root)), 3)
        self.assertEqual(self.run_main(), 1)

    def test_placeholders_are_clean(self) -> None:
        self.write("ok.txt", BS * 2 + "NAS" + BS + "share" + BS + "AfterburnerBackups\n"
                   + BS * 2 + "server" + BS + "share\n"
                   + "C:" + BS + "Users" + BS + "<you>" + BS + "\n127.0.0.1 0.0.0.0\n")
        self.assertEqual(privacy_scan.scan(self.root), [])
        self.assertEqual(self.run_main(), 0)

    def test_other_unc_flagged(self) -> None:
        self.write("unc.txt", BS * 2 + "homebox" + BS + "media" + BS + "x\n")
        self.assertEqual(len(privacy_scan.scan(self.root)), 1)

    def test_env_names_flagged_case_insensitive(self) -> None:
        self.write("env.txt", "hello ZZFakeUser\nhost zzfakepc here\nnothing\n")
        self.assertEqual([r[1] for r in privacy_scan.scan(self.root)], [1, 2])

    def test_cfg_file_flagged(self) -> None:
        self.write("Profile1.cfg", "[Startup]\n")
        self.assertEqual(len(privacy_scan.scan(self.root)), 1)

    def test_version_info_ip_like_ignored_and_binary_skipped(self) -> None:
        self.write("version_info.txt", "filevers=(1, 0, 0, 0) 1.0.0" + ".0\n")
        with open(os.path.join(self.root, "blob.bin"), "wb") as f:
            f.write(b"\0\1\2 someone" + b"@example.org")
        self.assertEqual(privacy_scan.scan(self.root), [])

    def test_skipped_folders(self) -> None:
        os.makedirs(os.path.join(self.root, ".git"))
        with open(os.path.join(self.root, ".git", "x.txt"), "w") as f:
            f.write("someone" + "@example.org")
        self.assertEqual(privacy_scan.scan(self.root), [])


if __name__ == "__main__":
    unittest.main()
