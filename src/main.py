"""Entry point for Afterburner Profile Backup: arguments, DPI, crash handler."""
import argparse
import sys
import tkinter as tk
import traceback

import settings
import ui_widgets


def _report(exc_type, exc, tb) -> None:
    settings.log("ERROR", "".join(traceback.format_exception(exc_type, exc, tb)))
    msg = ("Something went wrong. Nothing was deleted. Details were saved to %s."
           % settings.log_path())
    root = tk._default_root
    try:
        if root is None:
            raise tk.TclError("no window")
        ui_widgets.show_error(root, "Something went wrong", msg)
    except Exception:  # noqa: BLE001 - last resort
        print(msg)


def main() -> int:
    parser = argparse.ArgumentParser(description="Afterburner Profile Backup")
    parser.add_argument("--restore", action="store_true", help="start on the Restore screen")
    parser.add_argument("--test-run", action="store_true", help="start with Test run ticked")
    parser.add_argument("--selftest-ui", action="store_true", help="build every screen and exit")
    args = parser.parse_args()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001 - not Windows or already set
        pass
    sys.excepthook = _report
    tk.Tk.report_callback_exception = lambda self, t, e, tb: _report(t, e, tb)
    import ui
    return ui.run_app("restore" if args.restore else "home", args.selftest_ui, args.test_run)


if __name__ == "__main__":
    sys.exit(main())
