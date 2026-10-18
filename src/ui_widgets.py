"""Shared Tk widgets for Afterburner Profile Backup: fonts, buttons, status bar, dialogs."""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont, ttk
from typing import Any, Callable, Optional

SUCCESS_COLOR = "#1b5e20"
ERROR_COLOR = "#b71c1c"
_MARKERS = {"success": "✔ Done: ", "error": "✖ Problem: ",
            "info": "ℹ ", "warning": "⚠ Warning: "}
_FONTS: list = []


def setup_fonts(root: tk.Tk) -> None:
    """Create the named fonts once and the Big.TButton style (vista theme if available)."""
    family = "Segoe UI" if "Segoe UI" in tkfont.families(root) else \
        tkfont.nametofont("TkDefaultFont").actual("family")
    for name, size, weight in (("Body", 12, "normal"), ("Hint", 10, "normal"),
                               ("Title", 18, "bold"), ("Big", 16, "bold")):
        full = "ABPB." + name
        try:
            tkfont.nametofont(full, root).configure(family=family, size=size, weight=weight)
        except tk.TclError:
            # Keep a reference: Tk deletes a named font when its Font object is garbage collected.
            _FONTS.append(tkfont.Font(root=root, name=full, family=family, size=size,
                                      weight=weight))
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    style.configure("Big.TButton", font="ABPB.Big", padding=16)
    style.configure("Body.TButton", font="ABPB.Body", padding=6)
    style.configure("TCheckbutton", font="ABPB.Body")


def _wrap(label: ttk.Label) -> ttk.Label:
    label.bind("<Configure>", lambda e: label.configure(wraplength=max(e.width - 4, 100)))
    return label


def _button(parent, text, hint, command, style, font_name) -> ttk.Button:
    frame = ttk.Frame(parent)
    btn = ttk.Button(frame, text=text, command=command, style=style, takefocus=True)
    btn.pack(anchor="w")
    btn.bind("<Return>", lambda e: (btn.invoke(), "break")[1])
    if hint:
        labeled_hint(frame, hint).pack(anchor="w", fill="x", pady=(2, 0))
    return btn


def big_button(parent, text: str, hint: str, command) -> ttk.Button:
    """Large button inside its own frame with a hint below. Caller places button.master."""
    return _button(parent, text, hint, command, "Big.TButton", "ABPB.Big")


def small_button(parent, text: str, hint: str, command) -> ttk.Button:
    """Normal-size button inside its own frame with a hint below. Caller places button.master."""
    return _button(parent, text, hint, command, "Body.TButton", "ABPB.Body")


def labeled_hint(parent, text: str) -> ttk.Label:
    return _wrap(ttk.Label(parent, text=text, font="ABPB.Hint", justify="left"))


def title_label(parent, text: str) -> ttk.Label:
    return _wrap(ttk.Label(parent, text=text, font="ABPB.Title", justify="left"))


def body_label(parent, text: str) -> ttk.Label:
    return _wrap(ttk.Label(parent, text=text, font="ABPB.Body", justify="left"))


class StatusBar(ttk.Frame):
    """Bottom message area: selectable read-only text that starts with a marker."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._text = tk.Text(self, height=3, wrap="word", font="ABPB.Body", state="disabled",
                             relief="flat", borderwidth=0, takefocus=False)
        self._text.pack(fill="both", expand=True, padx=8, pady=6)
        self._text.tag_configure("success", foreground=SUCCESS_COLOR)
        self._text.tag_configure("error", foreground=ERROR_COLOR)

    def set(self, kind: str, text: str) -> None:
        marker = _MARKERS.get(kind, _MARKERS["info"])
        if not text.startswith(tuple(_MARKERS.values())):
            text = marker + text
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text, kind if kind in ("success", "error") else ())
        self._text.configure(state="disabled")

    def get_text(self) -> str:
        return self._text.get("1.0", "end-1c")


def zoom_factor(root: tk.Misc) -> float:
    """Windows display zoom as a factor (1.0 = 100%, 1.5 = 150%)."""
    try:
        return max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
    except (tk.TclError, ValueError):
        return 1.0


class ScrollArea(ttk.Frame):
    """Area whose content (self.inner) fills the space, and scrolls only when it doesn't fit.

    Keeps every screen usable at any Windows zoom level or window size."""

    _SELF_SCROLLING = ("Text", "Listbox", "Treeview", "Canvas")

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        bg = ttk.Style(self).lookup("TFrame", "background") or None
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=bg,
                                takefocus=False)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self._bar_shown = False
        self._last = None
        self.canvas.bind("<Configure>", lambda e: self._fit())
        # The content's wanted height changes without any event (new screen, re-wrapped
        # text), so check it a few times a second.
        self._after_id = self.after(150, self._poll)
        self.bind("<Destroy>", self._stop, add="+")
        root = self.winfo_toplevel()
        root.bind_all("<MouseWheel>", self._wheel, add="+")
        root.bind_all("<FocusIn>", self._focus, add="+")

    def _stop(self, event) -> None:
        if event.widget is self and self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _poll(self) -> None:
        try:
            key = (self.inner.winfo_reqheight(), self.canvas.winfo_width(),
                   self.canvas.winfo_height())
            if key != self._last:
                self._fit()
            self._after_id = self.after(150, self._poll)
        except tk.TclError:
            pass  # window closed

    def refresh(self) -> None:
        """Re-check the content size now (call after replacing the content)."""
        self.update_idletasks()
        self._fit()

    def _fit(self) -> None:
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        need = self.inner.winfo_reqheight()
        self._last = (need, width, height)
        full = max(height, need)
        self.canvas.itemconfigure(self._win, width=width, height=full)
        self.canvas.configure(scrollregion=(0, 0, width, full))
        if need > height + 1 and not self._bar_shown:
            self.bar.pack(side="right", fill="y", before=self.canvas)
            self._bar_shown = True
        elif need <= height and self._bar_shown:
            self.bar.pack_forget()
            self._bar_shown = False
            self.canvas.yview_moveto(0)

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0)

    def _inside(self, widget) -> bool:
        while widget is not None:
            if widget is self.inner:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _wheel(self, event) -> None:
        widget = event.widget
        if not self._bar_shown or not isinstance(widget, tk.Misc) or not self._inside(widget):
            return
        probe = widget
        while probe is not None and probe is not self.inner:  # lists scroll themselves
            if probe.winfo_class() in self._SELF_SCROLLING:
                return
            probe = probe.master
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _focus(self, event) -> None:
        """Scroll so the widget that just got keyboard focus is visible."""
        widget = event.widget
        if not self._bar_shown or not isinstance(widget, tk.Misc) or not self._inside(widget):
            return
        try:
            top = widget.winfo_rooty() - self.inner.winfo_rooty()
            bottom = top + widget.winfo_height()
            full = max(1, self.inner.winfo_height())
            view_top, view_bottom = (f * full for f in self.canvas.yview())
            if top < view_top:
                self.canvas.yview_moveto(max(0, top - 8) / full)
            elif bottom > view_bottom:
                self.canvas.yview_moveto((bottom + 8 - (view_bottom - view_top)) / full)
        except tk.TclError:
            pass


def run_background(root: tk.Misc, func: Callable[[], Any],
                   on_done: Callable[[Any, Any], None]) -> None:
    """Run func() in a daemon thread; call on_done(result, error) on the Tk thread."""
    box: dict = {}

    def work() -> None:
        try:
            box["result"] = func()
        except BaseException as exc:  # noqa: BLE001 - handed to on_done
            box["error"] = exc
        box["done"] = True

    def poll() -> None:
        if box.get("done"):
            on_done(box.get("result"), box.get("error"))
        else:
            root.after(100, poll)

    threading.Thread(target=work, daemon=True).start()
    root.after(100, poll)


def _dialog(parent, title: str, message: str, choices: list, default: int, cancel: Any) -> Any:
    """Modal dialog. choices = [(text, value)]. Esc/close return cancel."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent.winfo_toplevel())
    win.resizable(False, False)
    out = {"v": cancel}
    body = ttk.Frame(win, padding=16)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=message, font="ABPB.Body", wraplength=480, justify="left").pack(anchor="w")
    row = ttk.Frame(body)
    row.pack(anchor="e", pady=(16, 0))
    buttons = []

    def finish(value) -> None:
        out["v"] = value
        win.destroy()

    for text, value in choices:
        b = ttk.Button(row, text=text, style="Body.TButton", command=lambda v=value: finish(v))
        b.pack(side="left", padx=6)
        b.bind("<Return>", lambda e, bb=b: (bb.invoke(), "break")[1])
        buttons.append(b)
    win.bind("<Escape>", lambda e: finish(cancel))
    win.protocol("WM_DELETE_WINDOW", lambda: finish(cancel))
    win.update_idletasks()
    try:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        win.geometry("+%d+%d" % (px + 60, py + 60))
    except tk.TclError:
        pass
    win.grab_set()
    buttons[default].focus_set()
    parent.wait_window(win)
    return out["v"]


def confirm(parent, title: str, message: str, yes_text: str = "Yes", no_text: str = "No",
            default_no: bool = False) -> bool:
    """Modal Yes/No. Focus starts on Yes, or on No if default_no. Esc/close = No."""
    return _dialog(parent, title, message, [(yes_text, True), (no_text, False)],
                   1 if default_no else 0, False) is True


def show_info(parent, title: str, message: str) -> None:
    _dialog(parent, title, "ℹ " + message, [("OK", None)], 0, None)


def show_error(parent, title: str, message: str) -> None:
    _dialog(parent, title, "✖ Problem: " + message, [("OK", None)], 0, None)


def pick_folder(parent, title: str, initial: Optional[str]) -> Optional[str]:
    """Folder chooser. Returns a normalized path, or None if cancelled."""
    start = initial if initial and os.path.isdir(initial) else None
    chosen = filedialog.askdirectory(parent=parent, title=title, initialdir=start, mustexist=True)
    return os.path.normpath(chosen) if chosen else None


def _demo(auto_close: bool) -> int:
    root = tk.Tk()
    root.title("ui_widgets demo")
    setup_fonts(root)
    status = StatusBar(root)
    big_button(root, "Big Button", "A big hint.", lambda: status.set("success", "Big clicked.")
               ).master.pack(padx=16, pady=8, anchor="w")
    small_button(root, "Small Button", "A small hint.", lambda: status.set("info", "Small clicked.")
                 ).master.pack(padx=16, pady=8, anchor="w")
    status.pack(side="bottom", fill="x")
    kinds = iter(["info", "success", "warning", "error"])

    def cycle() -> None:
        k = next(kinds, None)
        if k:
            status.set(k, "Demo message (%s)." % k)
            root.after(500, cycle)
    cycle()
    if auto_close:
        root.after(3000, root.destroy)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(_demo("--auto-close" in sys.argv))
