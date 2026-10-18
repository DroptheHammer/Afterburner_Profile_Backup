"""Restore step 2: choose which profiles to put back, confirm, and run the restore."""
import tkinter as tk
from tkinter import ttk

import backup_core
import settings
import ui_widgets as w
import winutils
from ui import Screen

WORKING = "Working… please wait."


class RestoreSelectScreen(Screen):
    title = "Restore Profiles — Step 2 of 2: Choose profiles"

    def build(self) -> None:
        self.info = self.kwargs.get("backup")
        self.vars = {}
        self.restore_btn = None
        w.small_button(self, "Back", "", self.app.go_back).master.pack(anchor="w")
        w.title_label(self, self.title).pack(anchor="w", pady=(4, 8))
        if self.info is None:
            w.body_label(self, "Please pick a backup first.").pack(anchor="w", fill="x")
            return
        self.date_text = backup_core.friendly_datetime(self.info.created)
        w.body_label(self, "From the backup made on %s." % self.date_text
                     ).pack(anchor="w", fill="x", pady=(0, 8))
        self._build_list()
        row = ttk.Frame(self)
        for text, value in (("Select All", True), ("Select None", False)):
            b = ttk.Button(row, text=text, style="Body.TButton",
                           command=lambda v=value: self._set_all(v))
            b.bind("<Return>", lambda e, bb=b: (bb.invoke(), "break")[1])
            b.pack(side="left", padx=(0, 8))
        row.pack(anchor="w", pady=(8, 0))
        w.labeled_hint(self, "Tick the profiles you want to put back.").pack(anchor="w")
        w.body_label(self, "⚠ Warning: If Afterburner is set to apply settings when Windows "
                     "starts, a restored profile may be applied the next time you start your "
                     "PC.").pack(anchor="w", fill="x", pady=8)
        self.restore_btn = w.big_button(
            self, "Restore Selected Profiles",
            "We'll make a safety copy of your current profiles first.", self.start_restore)
        self.restore_btn.master.pack(anchor="w", pady=(0, 8))
        frame = ttk.Frame(self)
        self.details = tk.Text(frame, height=5, wrap="word", state="disabled", font="ABPB.Hint")
        bar = ttk.Scrollbar(frame, orient="vertical", command=self.details.yview)
        self.details.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.details.pack(side="left", fill="both", expand=True)
        frame.pack(fill="both", expand=True)

    def _build_list(self) -> None:
        outer = ttk.Frame(self)
        canvas = tk.Canvas(outer, height=170, highlightthickness=0)
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        for widget in (canvas, inner):
            widget.bind("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        for rec in self.info.files:
            name = rec.rel_path.split("/")[-1]
            if rec.rel_path == backup_core.MAIN_CFG_NAME:
                name += " (main Afterburner settings)"
            var = tk.BooleanVar(self, True)
            self.vars[rec.rel_path] = var
            cb = ttk.Checkbutton(inner, text="%s  —  %s" % (name, backup_core.friendly_size(
                rec.size)), variable=var)
            cb.pack(anchor="w", pady=2)
            cb.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        outer.pack(fill="x")

    def on_show(self) -> None:
        if self.restore_btn is not None:
            self.restore_btn.focus_set()
            self.app.status.set("info", "Choose the profiles to restore, then click the big button.")
        else:
            self.app.status.set("info", "Please pick a backup first.")

    def _set_all(self, value: bool) -> None:
        for var in self.vars.values():
            var.set(value)

    def _set_details(self, lines) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "\n".join(lines))
        self.details.configure(state="disabled")

    def _finish_busy(self) -> bool:
        """Return False if the screen is gone; otherwise re-enable the buttons."""
        if not self.winfo_exists():
            return False
        self.busy(False)
        return True

    def start_restore(self) -> None:
        app = self.app
        dry = bool(app.test_run.get())
        chosen = [r for r, v in self.vars.items() if v.get()]
        if not chosen:
            app.status.set("error", "Please pick at least one profile to restore.")
            return
        s = app.settings
        if not backup_core.is_valid_install_dir(s.install_dir) or not s.backup_root:
            app.status.set("error", "We can't find your Afterburner folder or backup folder. "
                           "Please set them in Settings first.")
            return
        if dry:
            self._confirm_and_run(chosen)
            return
        self.busy(True)
        app.status.set("info", WORKING)

        def done(running, error) -> None:
            if not self._finish_busy():
                return
            if error is not None:
                settings.log("ERROR", "Checking Afterburner failed: %r" % (error,))
                running = False
            if not running:
                self._confirm_and_run(chosen)
            elif w.confirm(app, "Afterburner is still open",
                           "MSI Afterburner is running. It needs to be closed first, otherwise "
                           "it may overwrite the restored profiles when it closes.\n\n"
                           "Shall we close Afterburner for you?",
                           yes_text="Close Afterburner for me", no_text="I'll close it myself"):
                self._close(chosen, False)
            else:
                app.status.set("info", "Please close Afterburner (right-click its icon near the "
                               "clock and choose Exit), then click Restore again.")

        w.run_background(app, winutils.is_afterburner_running, done)

    def _close(self, chosen, force: bool) -> None:
        app = self.app
        self.busy(True)
        app.status.set("info", WORKING)

        def done(result, error) -> None:
            if not self._finish_busy():
                return
            ok, reason = (False, "Afterburner could not be closed.") if error else result
            if ok:
                self._confirm_and_run(chosen)
            elif not force and w.confirm(app, "Afterburner didn't close",
                                         reason + "\n\nForce it to close?",
                                         yes_text="Force close", no_text="Cancel"):
                self._close(chosen, True)
            else:
                settings.log("ERROR", "Could not close Afterburner: " + reason)
                app.status.set("error", reason)

        w.run_background(app, lambda: winutils.close_afterburner(force=force), done)

    def _confirm_and_run(self, chosen) -> None:
        app = self.app
        s = app.settings
        dry = bool(app.test_run.get())
        names = [r.split("/")[-1] for r in chosen]
        lines = ["   • " + n for n in names[:12]]
        if len(names) > 12:
            lines.append("   • …and %d more" % (len(names) - 12))
        message = ("We will:\n1. Make a safety copy of your current profiles in %s\\before-restore."
                   "\n2. Replace %s in %s with the ones from %s:\n%s\n\nThis changes your "
                   "Afterburner settings. Continue?" % (
                       s.backup_root, backup_core.count_text(len(names)), s.install_dir,
                       self.date_text, "\n".join(lines)))
        title, yes = (("Test run — nothing will change", "Show me") if dry
                      else ("Restore these profiles?", "Yes, restore"))
        if not w.confirm(app, title, message, yes_text=yes, no_text="Cancel", default_no=True):
            app.status.set("info", "Nothing was changed.")
            return
        self._set_details([])
        self.busy(True)
        app.status.set("info", WORKING)

        def done(result, error) -> None:
            if not self._finish_busy():
                return
            if error is not None:
                settings.log("ERROR", "Restore crashed: %r" % (error,))
                app.status.set("error", "The restore did not finish. Nothing was deleted. "
                               "Details were saved to the log.")
                return
            self._set_details(result.details)
            settings.log("INFO" if result.ok else "ERROR", result.message)
            app.status.set(("info" if result.dry_run else "success") if result.ok else "error",
                           result.message)
            if result.ok and not result.dry_run:
                w.show_info(app, "Restore finished",
                            "Your profiles were restored and checked.\n\nPlease open MSI "
                            "Afterburner again. If it is set to apply settings when Windows "
                            "starts, the restored profile may apply next time you start your PC.")

        w.run_background(app, lambda: backup_core.restore_files(
            self.info, chosen, s.install_dir, s.backup_root,
            include_main_cfg=bool(s.include_main_cfg), dry_run=dry), done)
