"""Restore step 1: pick which backup to restore from."""
import tkinter as tk
from tkinter import ttk

import backup_core
import settings
import ui_widgets as w
import winutils
from ui import Screen


class RestoreScreen(Screen):
    title = "Restore Profiles — Step 1 of 2: Pick a backup"

    def build(self) -> None:
        self.infos: list = []
        w.small_button(self, "Back", "", self.app.go_back).master.pack(anchor="w")
        w.title_label(self, self.title).pack(anchor="w", pady=(4, 12))
        self.folder_label = w.body_label(self, "")
        self.folder_label.pack(anchor="w", fill="x")
        self.change_btn = w.small_button(self, "Choose a Different Folder…",
                                         "Use this if your backups are somewhere else.",
                                         self.change_folder)
        self.change_btn.master.pack(anchor="w", pady=(2, 10))
        self.empty_label = w.body_label(self, "")
        self.empty_label.pack(anchor="w", fill="x")
        box = ttk.Frame(self)
        self.listbox = tk.Listbox(box, selectmode="browse", height=10, font="ABPB.Body",
                                  exportselection=False)
        bar = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._update_next())
        self.listbox.bind("<Double-Button-1>", lambda e: self.go_next())
        self.listbox.bind("<Return>", lambda e: self.go_next())
        self.next_btn = w.small_button(self, "Next", "See the profiles in this backup and "
                                       "choose which to put back.", self.go_next)
        # Pack Next before the list so a small window shrinks the list, not the button.
        self.next_btn.master.pack(side="bottom", anchor="w")
        box.pack(fill="both", expand=True, pady=(0, 10))
        self._update_next()

    def on_show(self) -> None:
        self._show_folder()
        self.load()

    def _show_folder(self) -> None:
        self.folder_label.configure(
            text="Backup folder: %s" % (self.app.settings.backup_root or "not chosen yet"))

    def _update_next(self) -> None:
        self.next_btn.state(["!disabled" if self.listbox.curselection() else "disabled"])

    def load(self) -> None:
        root = self.app.settings.backup_root
        self.infos = []
        self.listbox.delete(0, "end")
        if not root:
            self._loaded([], None)
            return
        self.busy(True)
        self.app.status.set("info", "Working… please wait.")
        w.run_background(self.app, lambda: backup_core.list_backups(root), self._loaded)

    def _loaded(self, result, error) -> None:
        if not self.winfo_exists():
            return
        self.busy(False)
        if error is not None:
            settings.log("ERROR", "Listing backups failed: %r" % (error,))
            result = []
        self.infos = list(result or [])
        self.listbox.delete(0, "end")
        for info in self.infos:
            self.listbox.insert("end", backup_core.backup_label(info))
        self._update_next()
        if self.infos:
            self.empty_label.configure(text="")
            n = len(self.infos)
            settings.log("INFO", "Found %d backups to restore from." % n)
            self.app.status.set("info", "Found %d backup%s. Pick one, then click Next."
                                % (n, "" if n == 1 else "s"))
            self.listbox.focus_set()
        else:
            self.empty_label.configure(text="No backups were found in this folder. Make a backup "
                                       "first, or choose the folder where your backups are.")
            self.app.status.set("info", "No backups found. Make a backup first, or choose "
                                "the folder where your backups are.")
            self.change_btn.focus_set()

    def change_folder(self) -> None:
        app = self.app
        picked = w.pick_folder(app, "Choose the folder where your backups are",
                               app.settings.backup_root)
        if not picked:
            app.status.set("info", "Nothing was changed.")
            return
        app.settings.backup_root = winutils.to_unc_path(picked)
        app.save_settings()
        settings.log("INFO", "Backup folder changed on the Restore screen.")
        self._show_folder()
        self.load()

    def go_next(self) -> None:
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.infos) or "disabled" in self.next_btn.state():
            return
        self.app.show_screen("restore_select", backup=self.infos[sel[0]])
