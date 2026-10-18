"""Backup screen: choose a backup folder and copy the Afterburner profiles into a dated folder."""
import os
import tkinter as tk
from tkinter import ttk

import backup_core
import settings
import ui_widgets as w
import winutils
from ui import Screen


class BackupScreen(Screen):
    title = "Back Up My Profiles"

    def build(self) -> None:
        s = self.app.settings
        self.folder_var = tk.StringVar(self, s.backup_root or "")
        self.result_folder = None
        w.small_button(self, "Back", "", self.app.go_back).master.pack(anchor="w")
        w.title_label(self, "Back Up My Profiles").pack(anchor="w", pady=(4, 8))
        w.body_label(self, "Afterburner folder: %s" % (s.install_dir or "not found yet")
                     ).pack(anchor="w", fill="x")
        if backup_core.is_valid_install_dir(s.install_dir):
            n = len(backup_core.list_profile_files(s.install_dir, bool(s.include_main_cfg)))
            found = ("We found %s to back up." % backup_core.count_text(n)) if n else (
                "We didn't find any profiles to back up in this folder.")
        else:
            found = "We can't find your Afterburner folder. Please check it in Settings."
        w.body_label(self, found).pack(anchor="w", fill="x", pady=(0, 12))
        row = ttk.Frame(self)
        ttk.Label(row, text="Backup folder:", font="ABPB.Body").pack(side="left", padx=(0, 8))
        self.entry = ttk.Entry(row, textvariable=self.folder_var, state="readonly",
                               font="ABPB.Body")
        self.entry.pack(side="left", fill="x", expand=True)
        row.pack(fill="x")
        self.choose_btn = w.small_button(
            self, "Choose Folder…", "Pick where to keep your backups — for example a folder on "
            "another drive or your NAS.", self.choose_folder)
        self.choose_btn.master.pack(anchor="w", pady=(4, 12))
        self.test_label = ttk.Label(self, text="Test run is ON — nothing will be copied.",
                                    font="ABPB.Big")
        self.start_btn = w.big_button(
            self, "Start Backup", "Makes a new dated folder inside your backup folder and "
            "copies your profiles into it.", self.start_backup)
        self.start_btn.master.pack(anchor="w", pady=(0, 8))
        self.open_btn = w.small_button(self, "Open Backup Folder",
                                       "Shows the new backup in File Explorer.", self.open_folder)
        text_frame = ttk.Frame(self)
        self.details = tk.Text(text_frame, height=8, wrap="word", state="disabled",
                               font="ABPB.Hint")
        bar = ttk.Scrollbar(text_frame, orient="vertical", command=self.details.yview)
        self.details.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.details.pack(side="left", fill="both", expand=True)
        text_frame.pack(fill="both", expand=True, pady=(8, 0))
        self._refresh()

    def _refresh(self) -> None:
        """Apply the show/hide and enable rules that depend on settings and test run."""
        if self.app.test_run.get():
            self.test_label.pack(anchor="w", pady=(0, 8), before=self.start_btn.master)
        else:
            self.test_label.pack_forget()
        has_folder = bool(self.app.settings.backup_root)
        self.start_btn.state(["!disabled" if has_folder else "disabled"])

    def on_show(self) -> None:
        self._refresh()
        if self.app.settings.backup_root:
            self.start_btn.focus_set()
        else:
            self.choose_btn.focus_set()
        if not self.app.settings.backup_root:
            self.app.status.set("info", "Choose a backup folder first, then click Start Backup.")
        else:
            self.app.status.set("info", "Ready. Click Start Backup.")

    def choose_folder(self) -> None:
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
            self._refresh()
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
            self.folder_var.set(path)
            self._refresh()
            self.start_btn.focus_set()
            settings.log("INFO", "Backup folder saved.")
            app.status.set("info", "Backup folder saved.")

        w.run_background(app, lambda: backup_core.check_folder_writable(path), done)

    def start_backup(self) -> None:
        app = self.app
        s = app.settings
        if not s.backup_root:
            app.status.set("error", "Please choose a backup folder first.")
            return
        dry = bool(app.test_run.get())
        self.open_btn.master.pack_forget()
        self._set_details([])
        self.busy(True)
        app.status.set("info", "Working… please wait.")

        def done(result, error) -> None:
            if not self.winfo_exists():
                return
            self.busy(False)
            self._refresh()
            if error is not None:
                settings.log("ERROR", "Backup crashed: %r" % (error,))
                app.status.set("error", "The backup did not finish. Your original profiles "
                               "were not changed. Details were saved to the log.")
                return
            self._set_details(result.details)
            settings.log("INFO" if result.ok else "ERROR", result.message)
            app.status.set(("info" if result.dry_run else "success") if result.ok else "error",
                           result.message)
            if result.ok and not result.dry_run and result.folder:
                self.result_folder = result.folder
                self.open_btn.master.pack(anchor="w", pady=(8, 0), before=self.details.master)

        w.run_background(app, lambda: backup_core.create_backup(
            s.install_dir or "", s.backup_root, bool(s.include_main_cfg), dry_run=dry), done)

    def _set_details(self, lines) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "\n".join(lines))
        self.details.configure(state="disabled")

    def open_folder(self) -> None:
        try:
            os.startfile(self.result_folder)  # type: ignore[attr-defined]
        except (OSError, AttributeError, TypeError) as exc:
            settings.log("ERROR", "Could not open backup folder: %r" % (exc,))
            self.app.status.set("error", "We couldn't open the folder. It is here: %s"
                                % self.result_folder)
