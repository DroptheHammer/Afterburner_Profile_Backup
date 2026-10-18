r"""Create a fake MSI Afterburner folder for manual testing.

Usage: py tools\make_fake_install.py <folder>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers import make_fake_install  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Please give a folder to put the fake install in.")
        print(r"Example: py tools\make_fake_install.py C:\Users\<you>\fake")
        return 2
    path = make_fake_install(os.path.abspath(argv[1]))
    print("Fake Afterburner folder created at: " + path)
    print("To use it in this window, run:")
    print("set ABPB_TEST_INSTALL_DIR=" + path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
