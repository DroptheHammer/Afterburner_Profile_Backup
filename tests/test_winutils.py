"""Tests for winutils (safe ones only: no closing processes, no UAC prompts)."""
import os
import sys
import tempfile
import unittest

from tests.helpers import add_src_to_path, make_fake_install

add_src_to_path()
import winutils  # noqa: E402


class WinutilsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old = os.environ.get("ABPB_TEST_INSTALL_DIR")

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("ABPB_TEST_INSTALL_DIR", None)
        else:
            os.environ["ABPB_TEST_INSTALL_DIR"] = self._old

    def test_is_windows(self) -> None:
        self.assertEqual(winutils.is_windows(), sys.platform == "win32")

    def test_process_paths(self) -> None:
        paths = winutils.find_afterburner_process_paths()
        self.assertIsInstance(paths, list)
        for p in paths:
            self.assertTrue(p.lower().endswith("msiafterburner.exe"))

    def test_is_running_returns_bool(self) -> None:
        self.assertIsInstance(winutils.is_afterburner_running(), bool)

    def test_find_install_dir_test_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install = make_fake_install(tmp)
            os.environ["ABPB_TEST_INSTALL_DIR"] = install
            self.assertEqual(winutils.find_install_dir(), (install, "test"))

    def test_find_install_dir_returns_pair(self) -> None:
        os.environ.pop("ABPB_TEST_INSTALL_DIR", None)
        folder, how = winutils.find_install_dir()
        self.assertIn(how, ("running", "registry", "default", "none"))
        self.assertEqual(folder is None, how == "none")

    def test_to_unc_path_local_unchanged(self) -> None:
        tmp = tempfile.gettempdir()
        self.assertEqual(winutils.to_unc_path(tmp), tmp)
        self.assertEqual(winutils.to_unc_path(""), "")

    def test_run_hidden(self) -> None:
        if not winutils.is_windows():
            self.skipTest("Windows only")
        code, out = winutils.run_hidden(["cmd", "/c", "echo", "hi"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("hi"))

    def test_run_hidden_bad_command(self) -> None:
        code, out = winutils.run_hidden(["this-command-does-not-exist-abpb"])
        self.assertEqual(code, -1)
        self.assertIsInstance(out, str)

    def test_is_admin_bool(self) -> None:
        self.assertIsInstance(winutils.is_admin(), bool)

    def test_default_install_dirs(self) -> None:
        self.assertEqual(len(winutils.default_install_dirs()), 2)

    def test_registry_install_dirs_list(self) -> None:
        self.assertIsInstance(winutils.registry_install_dirs(), list)

    def test_folder_from_command(self) -> None:
        f = winutils._folder_from_command
        self.assertEqual(f('"C:\\Apps\\MSI Afterburner\\uninstall.exe",0'),
                         "C:\\Apps\\MSI Afterburner")
        self.assertEqual(f('C:\\Apps\\AB\\Uninstall.exe /S'), "C:\\Apps\\AB")
        self.assertEqual(f(""), "")


if __name__ == "__main__":
    unittest.main()
