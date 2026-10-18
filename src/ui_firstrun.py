"""First-run screen: finds the Afterburner folder and asks the user to confirm it."""
import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import backup_core
import settings
import ui_widgets as w
import winutils
from ui import Screen

NOT_FOUND_BODY = ("Please show us where it is installed. It is usually "
                  "C:\\Program Files (x86)\\MSI Afterburner.")
PICK_HINT = ("Choose the MSI Afterburner folder yourself. "
             "It is usually in Program Files (x86).")
BAD_FOLDER = ("That folder doesn't look like MSI Afterburner. "
              "It should contain a folder named Profiles.")


class FirstRunScreen(Screen):
    title = "Is this correct?"

    def build(self) -> None:
        self.folder: str | None = None
        self.main_btn = None
        self.back_btn = w.small_button(self, "Back", "", self.app.go_back)
        self.back_btn.master.pack(anchor="w", pady=(0, 8))
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True)
        self.app.status.set("info", "Working… please wait.")
        self.busy(True)
        w.run_background(self.app, winutils.find_install_dir, self._found)

    def on_show(self) -> None:
        self.back_btn.focus_set()

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _found(self, result, error) -> None:
        if not self._alive():
            return
        self.busy(False)
        folder = None
        if error is not None:
            settings.log("ERROR", "Searching for Afterburner failed: %s" % error)
        elif result:
            folder, how = result
            settings.log("INFO", "Afterburner search: %s (%s)" % (folder or "nothing", how))
        self.render(folder)

    def render(self, folder: str | None) -> None:
        """Show the list for `folder`, or the 'not found' text when folder is None."""
        for child in self.content.winfo_children():
            child.destroy()
        self.folder = folder
        c = self.content
        if folder:
            w.title_label(c, "We found your Afterburner profiles here. Is this correct?"
                          ).pack(anchor="w")
            w.body_label(c, folder).pack(anchor="w", fill="x", pady=(4, 8))
            self._build_list(c, folder)
            row = ttk.Frame(c)
            row.pack(anchor="w", pady=8)
            self.main_btn = w.small_button(row, "Yes, that's right", "Use this folder.", self.yes)
            self.main_btn.master.pack(side="left", padx=(0, 16), anchor="n")
            w.small_button(row, "No, let me pick the folder", PICK_HINT, self.pick
                           ).master.pack(side="left", anchor="n")
            self.app.status.set("info", "Please check the folder and choose Yes or No.")
        else:
            w.title_label(c, "We couldn't find MSI Afterburner automatically.").pack(anchor="w")
            w.body_label(c, NOT_FOUND_BODY).pack(anchor="w", fill="x", pady=(4, 8))
            self.main_btn = w.small_button(c, "Pick the folder…", PICK_HINT, self.pick)
            self.main_btn.master.pack(anchor="w", pady=8)
            self.app.status.set("warning", "We couldn't find Afterburner. Please pick its folder.")
        self.main_btn.focus_set()

    def _build_list(self, parent, folder: str) -> None:
        box = ttk.Frame(parent)
        box.pack(fill="both", expand=True)
        tree = ttk.Treeview(box, columns=("Name", "Size", "Last changed"), show="headings",
                            height=8)
        for col, width in (("Name", 380), ("Size", 100), ("Last changed", 220)):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w")
        bar = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for pf in backup_core.list_profile_files(folder, True):
            tree.insert("", "end", values=(
                os.path.basename(pf.abs_path), backup_core.friendly_size(pf.size),
                backup_core.friendly_datetime(datetime.fromtimestamp(pf.modified))))

    def yes(self) -> None:
        if not self.folder:
            return
        s = self.app.settings
        s.install_dir = self.folder
        s.install_confirmed = True
        self.app.save_settings()
        settings.log("INFO", "Afterburner folder confirmed: %s" % self.folder)
        self.app.go_home()
        self.app.status.set("success", "Afterburner folder saved.")

    def pick(self) -> None:
        picked = w.pick_folder(self.app, "Choose the MSI Afterburner folder", self.folder)
        if picked is None:
            self.app.status.set("info", "No folder was chosen. Nothing was changed.")
            return
        if backup_core.is_valid_install_dir(picked):
            settings.log("INFO", "Afterburner folder picked: %s" % picked)
            self.render(picked)
        else:
            settings.log("WARN", "Picked folder is not an Afterburner folder: %s" % picked)
            w.show_error(self.app, "Wrong folder", BAD_FOLDER)
            self.app.status.set("error", BAD_FOLDER + " Please try again.")
