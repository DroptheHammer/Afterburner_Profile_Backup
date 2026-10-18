"""App window, screen switching and the Home screen for Afterburner Profile Backup."""
import importlib
import tkinter as tk
from tkinter import ttk

import backup_core
import settings
import ui_widgets as w
import winutils
from version import APP_NAME

SCREENS: dict[str, tuple[str, str]] = {
    "home": ("ui", "HomeScreen"),
    "firstrun": ("ui_firstrun", "FirstRunScreen"),
    "backup": ("ui_backup", "BackupScreen"),
    "restore": ("ui_restore", "RestoreScreen"),
    "restore_select": ("ui_restore_select", "RestoreSelectScreen"),
    "settings": ("ui_settings", "SettingsScreen"),
    "help": ("ui_help", "HelpScreen"),
}


class Screen(ttk.Frame):
    """Base class for screens. Subclasses implement build() and may override on_show()."""
    title: str = ""

    def __init__(self, app: "App", **kwargs):
        super().__init__(app.screen_area, padding=16)
        self.app = app
        self.kwargs = kwargs
        self.build()

    def build(self) -> None:
        pass

    def on_show(self) -> None:
        pass

    def busy(self, is_busy: bool) -> None:
        state = "disabled" if is_busy else "!disabled"

        def walk(widget) -> None:
            for child in widget.winfo_children():
                if isinstance(child, (ttk.Button, ttk.Checkbutton)):
                    child.state([state])
                walk(child)
        walk(self)


class PlaceholderScreen(Screen):
    """Shown when a screen's module has not been built yet."""
    title = "Not built yet"

    def build(self) -> None:
        w.title_label(self, "Coming soon").pack(anchor="w")
        w.body_label(self, "This part of the app isn't built yet.").pack(anchor="w", fill="x")
        w.small_button(self, "Back", "", self.app.go_back).master.pack(anchor="w", pady=12)


class HomeScreen(Screen):
    title = APP_NAME

    def build(self) -> None:
        app = self.app
        w.title_label(self, APP_NAME).pack(anchor="w")
        w.body_label(self, "Keep a safe copy of your MSI Afterburner profiles, and put them "
                     "back when you need them.").pack(anchor="w", fill="x", pady=(4, 12))
        self.backup_btn = w.big_button(
            self, "Back Up My Profiles", "Copies your current profiles to your backup folder. "
            "Nothing is changed in Afterburner.", lambda: app.show_screen("backup"))
        self.backup_btn.master.pack(anchor="w", pady=6)
        w.big_button(self, "Restore Profiles", "Puts profiles from an earlier backup back "
                     "into Afterburner.", self.restore).master.pack(anchor="w", pady=6)
        row = ttk.Frame(self)
        ttk.Checkbutton(row, text="Test run (don't change anything)", variable=app.test_run
                        ).pack(anchor="w")
        w.labeled_hint(row, "Shows exactly what would happen, without copying anything."
                       ).pack(anchor="w")
        row.pack(anchor="w", pady=8, fill="x")
        small = ttk.Frame(self)
        for text, hint, cmd in (("Settings", "Change folders and options.",
                                 lambda: app.show_screen("settings")),
                                ("Help", "Step-by-step guide.", lambda: app.show_screen("help")),
                                ("About", "Version and license.", self.about)):
            w.small_button(small, text, hint, cmd).master.pack(side="left", padx=(0, 16))
        small.pack(anchor="w", pady=8)
        s = app.settings
        w.body_label(self, "Afterburner folder: %s\nBackup folder: %s" % (
            s.install_dir or "not found yet", s.backup_root or "not chosen yet")
        ).pack(anchor="w", fill="x", pady=8)

    def on_show(self) -> None:
        self.backup_btn.focus_set()
        self.app.status.set("info", "Ready. Choose Back Up or Restore.")

    def about(self) -> None:
        try:
            import ui_help
        except ModuleNotFoundError as exc:
            if exc.name != "ui_help":
                raise
            w.show_info(self.app, "About", "Coming soon.")
            return
        ui_help.show_about(self.app)

    def restore(self) -> None:
        app = self.app
        if winutils.is_windows() and not winutils.is_admin():
            if not w.confirm(app, "Administrator permission needed",
                             "Restoring puts files back into the MSI Afterburner folder, which "
                             "Windows protects. Windows will now ask for permission. Click Yes "
                             "in that window to continue.", yes_text="Continue",
                             no_text="Cancel"):
                return
            extra = ["--restore"] + (["--test-run"] if app.test_run.get() else [])
            if winutils.relaunch_as_admin(extra):
                app.destroy()
            else:
                app.status.set("error", "✖ Problem: Windows permission was not given, so we "
                               "can't restore. You can still make backups.")
            return
        app.show_screen("restore")


class App(tk.Tk):
    def __init__(self, start_screen: str = "home", test_run: bool = False,
                 selftest: bool = False):
        super().__init__()
        self.title(APP_NAME)
        w.setup_fonts(self)
        self._size_for_zoom()
        self.settings = settings.load_settings()
        self.test_run = tk.BooleanVar(self, bool(test_run))
        self.history: list[str] = []
        self.current: Screen | None = None
        self.current_name = ""
        self.status = w.StatusBar(self)
        self.status.pack(side="bottom", fill="x")
        self.scroll = w.ScrollArea(self)
        self.scroll.pack(side="top", fill="both", expand=True)
        self.screen_area = self.scroll.inner
        self.bind("<Escape>", lambda e: self.go_back() if self.current_name != "home" else None)
        if selftest:
            return
        s = self.settings
        if start_screen == "home" and (not s.install_confirmed
                                       or not backup_core.is_valid_install_dir(s.install_dir)):
            start_screen = "firstrun"
        self.show_screen(start_screen)

    def show_screen(self, name: str, **kwargs) -> None:
        mod_name, cls_name = SCREENS.get(name, ("", ""))
        cls = PlaceholderScreen
        if mod_name:
            try:
                cls = getattr(importlib.import_module(mod_name), cls_name, PlaceholderScreen)
            except ModuleNotFoundError as exc:
                if exc.name != mod_name:
                    raise
        if self.current is not None:
            self.current.destroy()
        self.current_name = name if name in SCREENS else "unknown"
        if not self.history or self.history[-1] != name:
            self.history.append(name)
        self.current = cls(self, **kwargs)
        self.current.pack(fill="both", expand=True)
        self.scroll.refresh()
        self.scroll.scroll_to_top()
        self.current.on_show()

    def _size_for_zoom(self) -> None:
        """Start and minimum size grow with Windows zoom, but never beyond the screen."""
        zoom = w.zoom_factor(self)
        max_w = int(self.winfo_screenwidth() * 0.9)
        max_h = int(self.winfo_screenheight() * 0.85)
        self.minsize(min(int(720 * zoom), max_w), min(int(560 * zoom), max_h))
        self.geometry("%dx%d" % (min(int(900 * zoom), max_w), min(int(680 * zoom), max_h)))

    def go_back(self) -> None:
        if self.history:
            self.history.pop()
        prev = self.history.pop() if self.history else "home"
        self.show_screen(prev)

    def go_home(self) -> None:
        self.history.clear()
        self.show_screen("home")

    def save_settings(self) -> None:
        if not settings.save_settings(self.settings):
            self.status.set("error", "We couldn't save your settings. Details are in the log.")


def run_app(start_screen: str = "home", selftest: bool = False, test_run: bool = False) -> int:
    app = App(start_screen, test_run, selftest=selftest)
    if not selftest:
        app.mainloop()
        return 0
    failed = 0
    try:
        from tkinter import font as tkfont
        if abs(int(tkfont.nametofont("ABPB.Title", app).actual("size"))) != 18:
            raise RuntimeError("ABPB.Title is not 18 pt")
        print("OK fonts")
    except Exception as exc:  # noqa: BLE001 - reported like a screen
        failed += 1
        print("FAIL fonts: %s" % exc)
    for name in SCREENS:
        try:
            app.show_screen(name, **({"backup": None} if name == "restore_select" else {}))
            app.update()
            if isinstance(app.current, PlaceholderScreen):
                raise RuntimeError("screen module missing (not built or not bundled)")
            print("OK " + name)
        except Exception as exc:  # noqa: BLE001 - reported per screen
            failed += 1
            print("FAIL %s: %s" % (name, exc))
    app.destroy()
    return 1 if failed else 0
