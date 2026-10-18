"""Smoke test: build every screen through `main.py --selftest-ui`."""
import os
import subprocess
import sys
import tempfile
import unittest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _has_display() -> bool:
    try:
        import tkinter as tk
        tk.Tk().destroy()
        return True
    except Exception:  # noqa: BLE001 - TclError or missing tkinter
        return False


class UiSmokeTest(unittest.TestCase):
    @unittest.skipUnless(_has_display(), "no display available")
    def test_selftest_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ABPB_SETTINGS_DIR=tmp)
            proc = subprocess.run([sys.executable, os.path.join(_REPO, "src", "main.py"),
                                   "--selftest-ui"], capture_output=True, text=True,
                                  timeout=60, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("OK home", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)


if __name__ == "__main__":
    unittest.main()
