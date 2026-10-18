"""Settings screen: change folders, the main-settings option, and open the log file."""
import os
import tkinter as tk
from tkinter import ttk

import backup_core
import settings
import ui_widgets as w
import winutils
from ui import Screen


class SettingsScreen(Screen):
    title = "Settings"

    def build(self) -> None:
        s = self.app.settings
        w.small_button(self, "Back", "", self.app.go_back).master.pack(anchor="w")
        w.title_label(self, "Settings").pack(anchor="w", pady=(4, 12))
        self.install_label = w.body_label(self, "")
        self.install_label.pack(anchor="w", fill="x")
        self._show_install()
        w.small_button(self, "Change…", "Only change this if we found the wrong folder.",
                       self.change_install).master.pack(anchor="w", pady=(2, 6))
        self.find_btn = w.small_button(self, "Find it again automatically",
                                       "Search for MSI Afterburner again.",
                                       lambda: self.app.show_screen("firstrun"))
        self.find_btn.master.pack(anchor="w", pady=(0, 16))
        self.backup_label = w.body_label(self, "")
        self.backup_label.pack(anchor="w", fill="x")
        self._show_backup()
        self.backup_btn = w.small_button(self, "Change…", "Where your backups are saved.",
                                         self.change_backup)
        self.backup_btn.master.pack(anchor="w", pady=(2, 16))
        self.include_var = tk.BooleanVar(self, bool(s.include_main_cfg))
        row = ttk.Frame(self)
        ttk.Checkbutton(row, text="Also back up the main Afterburner settings file",
                        variable=self.include_var, command=self.toggle_main_cfg).pack(anchor="w")
        w.labeled_hint(row, "Recommended. This file holds Afterburner's general options "
                       "(MSIAfterburner.cfg).").pack(anchor="w", fill="x")
        row.pack(anchor="w", fill="x", pady=(0, 16))
        w.small_button(self, "Open Log File", "For troubleshooting. Shows what the app did.",
                       self.open_log).master.pack(anchor="w")

    def _show_install(self) -> None:
        self.install_label.configure(
            text="Afterburner folder: %s" % (self.app.settings.install_dir or "not found yet"))

    def _show_backup(self) -> None:
        self.backup_label.configure(
            text="Backup folder: %s" % (self.app.settings.backup_root or "not chosen yet"))

    def on_show(self) -> None:
        self.find_btn.focus_set()
        self.app.status.set("info", "Change a setting below, or click Back.")

    def change_install(self) -> None:
        app = self.app
        picked = w.pick_folder(app, "Choose the MSI Afterburner folder", app.settings.install_dir)
        if not picked:
            app.status.set("info", "Nothing was changed.")
            return
        if not backup_core.is_valid_install_dir(picked):
            settings.log("WARN", "Picked folder is not an Afterburner folder.")
            w.show_error(app, "Not the right folder", "That folder doesn't look like MSI "
                         "Afterburner. It should contain a folder named Profiles.")
            app.status.set("error", "That folder doesn't look like MSI Afterburner.")
            return
        app.settings.install_dir = picked
        app.settings.install_confirmed = True
        app.save_settings()
        self._show_install()
        settings.log("INFO", "Afterburner folder changed in Settings.")
        app.status.set("success", "Afterburner folder saved.")

    def change_backup(self) -> None:
        app = self.app
        picked = w.pick_folder(app, "Choose your backup folder", app.settings.backup_root)
        if not picked:
            app.status.set("info", "Nothing was changed.")
            return
        path = winutils.to_unc_path(picked)
        self.busy(True)
        app.status.set("info", "Working… please wait.")

        def done(result, error) -> None:
            if not self.winfo_exists():
                return
            self.busy(False)
            if error is not None:
                settings.log("ERROR", "Checking backup folder failed: %r" % (error,))
                app.status.set("error", "We couldn't check that folder. Please try another one.")
                return
            ok, message = result
            if not ok:
                settings.log("WARN", "Backup folder not usable: " + message)
                app.status.set("error", message)
                return
            app.settings.backup_root = path
            app.save_settings()
            self._show_backup()
            settings.log("INFO", "Backup folder changed in Settings.")
            app.status.set("info", "Backup folder saved.")

        w.run_background(app, lambda: backup_core.check_folder_writable(path), done)

    def toggle_main_cfg(self) -> None:
        on = bool(self.include_var.get())
        self.app.settings.include_main_cfg = on
        self.app.save_settings()
        settings.log("INFO", "Include main settings file: %s" % on)
        self.app.status.set("info", "The main Afterburner settings file will %sbe backed up."
                            % ("" if on else "not "))

    def open_log(self) -> None:
        path = settings.log_path()
        if not os.path.exists(path):
            w.show_info(self.app, "Log file", "There is no log yet.")
            self.app.status.set("info", "There is no log yet.")
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except (OSError, AttributeError) as exc:
            settings.log("ERROR", "Could not open log file: %r" % (exc,))
            self.app.status.set("error", "We couldn't open the log file. It is here: " + path)
            return
        self.app.status.set("info", "Opened the log file.")
