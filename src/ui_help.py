"""Help screen (QUICKSTART guide) and About box for Afterburner Profile Backup."""
import tkinter as tk
from tkinter import ttk

import settings
import ui_widgets as w
from ui import Screen
from version import APP_NAME, DISCLAIMER, LICENSE_NAME, REPO_URL, VERSION


class HelpScreen(Screen):
    title = "Help"

    def build(self) -> None:
        w.small_button(self, "Back", "", self.app.go_back).master.pack(anchor="w")
        w.title_label(self, "Help").pack(anchor="w", pady=(4, 8))
        body = ttk.Frame(self)
        scroll = ttk.Scrollbar(body, orient="vertical")
        self.text = tk.Text(body, font="ABPB.Body", wrap="word", takefocus=True,
                            yscrollcommand=scroll.set, padx=8, pady=8)
        scroll.configure(command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        body.pack(fill="both", expand=True)
        self.text.tag_configure("heading", font="ABPB.Title")
        for line in settings.read_help_text().splitlines():
            if line.startswith("#"):
                self.text.insert("end", line.lstrip("#").lstrip() + "\n", "heading")
            else:
                self.text.insert("end", line + "\n")
        self.text.configure(state="disabled")

    def on_show(self) -> None:
        self.text.focus_set()
        self.app.status.set("info", "Here is the step-by-step guide. Press Esc to go back.")


def show_about(app) -> None:
    w.show_info(app, "About", f"{APP_NAME}\nVersion {VERSION}\n{LICENSE_NAME}\n\n"
                f"{DISCLAIMER}\n\nNo data ever leaves your PC.\n\n"
                f"Updates and source code:\n{REPO_URL}")
