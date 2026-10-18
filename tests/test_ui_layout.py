"""Layout tests: screens must stay usable at common Windows zoom levels (100% to 200%)."""
import os
import shutil
import tempfile
import unittest

from tests import helpers

helpers.add_src_to_path()

try:
    import tkinter as tk
    _root = tk.Tk()
    _root.destroy()
    HAVE_DISPLAY = True
except Exception:  # noqa: BLE001 - no display (e.g. CI without a desktop)
    HAVE_DISPLAY = False

ZOOMS = (1.0, 1.25, 1.5, 2.0)


def _laid_out(widget, screen) -> bool:
    """True if the widget and its parents are placed by a layout manager (not deliberately
    hidden with pack_forget). A squeezed-out button is still laid out, so it counts."""
    while widget is not None and widget is not screen:
        if not widget.winfo_manager():
            return False
        widget = widget.master
    return True


def _buttons(widget):
    found = []
    for child in widget.winfo_children():
        if child.winfo_class() == "TButton":
            found.append(child)
        found += _buttons(child)
    return found


@unittest.skipUnless(HAVE_DISPLAY, "needs a display")
class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old_env = dict(os.environ)
        os.environ["ABPB_SETTINGS_DIR"] = os.path.join(self.tmp, "settings")
        import backup_core
        import settings
        install = helpers.make_fake_install(self.tmp)
        root = os.path.join(self.tmp, "backups")
        os.makedirs(root)
        backup_core.create_backup(install, root)
        self.backup = backup_core.list_backups(root)[0]
        settings.save_settings(settings.Settings(install, True, root, True))

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _app_at_zoom(self, zoom):
        import ui
        import ui_widgets
        app = ui.App(selftest=True)
        app.tk.call("tk", "scaling", 96 * zoom / 72)  # what Windows zoom does to Tk
        ui_widgets.setup_fonts(app)
        app._size_for_zoom()
        app.update()
        return app

    def _visible(self, app, widget):
        app.update()
        canvas = app.scroll.canvas
        top, bottom = canvas.winfo_rooty(), canvas.winfo_rooty() + canvas.winfo_height()
        w_top = widget.winfo_rooty()
        return top - 1 <= w_top and w_top + widget.winfo_height() <= bottom + 1

    def test_home_fits_at_start_size(self):
        for zoom in ZOOMS:
            app = self._app_at_zoom(zoom)
            try:
                app.show_screen("home")
                app.update()
                capped = app.winfo_height() < int(680 * zoom) - 5  # small screen: may scroll
                for btn in _buttons(app.current):
                    self.assertGreaterEqual(btn.winfo_height(), btn.winfo_reqheight(),
                                            "%s squeezed at %d%%" % (btn.cget("text"), zoom * 100))
                    if not capped:
                        self.assertTrue(self._visible(app, btn),
                                        "%s cut off at %d%%" % (btn.cget("text"), zoom * 100))
            finally:
                app.destroy()

    def test_too_small_window_scrolls_instead_of_squeezing(self):
        """Small laptop screen: the window can't grow, so screens must scroll."""
        app = self._app_at_zoom(1.5)
        try:
            app.minsize(1, 1)
            app.geometry("800x420")
            for name, kwargs in (("home", {}), ("settings", {}),
                                 ("restore_select", {"backup": self.backup})):
                app.show_screen(name, **kwargs)
                app.update()
                self.assertTrue(app.scroll._bar_shown, "no scrollbar on %s" % name)
                for btn in _buttons(app.current):
                    if not _laid_out(btn, app.current):
                        continue
                    self.assertGreaterEqual(btn.winfo_height(), btn.winfo_reqheight(),
                                            "%s squeezed on %s" % (btn.cget("text"), name))
                    btn.focus_force()
                    app.update()
                    self.assertTrue(self._visible(app, btn),
                                    "%s on %s not scrolled into view" % (btn.cget("text"), name))
        finally:
            app.destroy()

    def test_every_button_reachable_at_min_size(self):
        screens = [("home", {}), ("firstrun", {}), ("backup", {}), ("restore", {}),
                   ("restore_select", {"backup": self.backup}), ("settings", {}), ("help", {})]
        for zoom in ZOOMS:
            app = self._app_at_zoom(zoom)
            try:
                min_w, min_h = app.minsize()
                app.geometry("%dx%d" % (min_w, min_h))
                for name, kwargs in screens:
                    app.show_screen(name, **kwargs)
                    app.update()
                    for btn in _buttons(app.current):
                        if not _laid_out(btn, app.current):
                            continue  # deliberately hidden, e.g. "Open Backup Folder"
                        self.assertGreaterEqual(
                            btn.winfo_height(), btn.winfo_reqheight(), "%s on %s squeezed at %d%%"
                            % (btn.cget("text"), name, zoom * 100))
                        btn.focus_force()
                        app.update()
                        self.assertTrue(self._visible(app, btn), "%s on %s not reachable at %d%%"
                                        % (btn.cget("text"), name, zoom * 100))
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
