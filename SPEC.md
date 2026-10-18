# Afterburner Profile Backup — Specification

Version of this spec: 1.0 (app version 1.0.0)

This file is the single source of truth. Every build step in `PLAN.md` must be
doable with only this file plus that one step. If this file and a step disagree,
this file wins. Do not invent features, files, or function names that are not
listed here.

---

## 1. What the app is

A small, free, open-source (MIT) Windows app that backs up and restores
MSI Afterburner profiles. Users are ordinary gamers, not technical people.

Hard rules:

- Opens with one double-click of a single `.exe`. No command line, no
  PowerShell, no installed runtime (no Python, no .NET install) for the user.
- Never deletes user data. Never fails silently.
- No network calls, no telemetry, nothing uploaded. The app only writes to:
  the backup folder the user chose, the Afterburner folder (only during a
  confirmed restore), and its own settings folder
  (`%LOCALAPPDATA%\AfterburnerProfileBackup`).
- No personal data in the repository (see section 12).

---

## 2. Tech stack

| Part | Choice |
|---|---|
| Language | Python 3.10 or newer (developer machine only). Use only the standard library at runtime. |
| GUI | `tkinter` + `tkinter.ttk` (standard library). No third-party GUI packages. |
| Windows APIs | `ctypes` and `winreg` (standard library). No `psutil`, no `pywin32`. |
| Tests | `unittest` (standard library). Run with `python -m unittest discover -s tests -v`. No pytest needed. |
| Packaging | PyInstaller (developer-only dependency), `--onefile --windowed`. |
| Build | `build.bat` — one command, produces `dist\AfterburnerProfileBackup.exe`. |

### 2.1 Design decisions that differ from the original brief (and why)

1. **Admin rights: ask only when restoring, not at every launch.**
   The brief asked for a UAC "require administrator" manifest. Problem: an
   app that always runs as administrator **cannot see mapped network drives**
   (like `Z:`) that the user mapped normally — Windows keeps those separate
   for admin apps. Many users back up to a NAS through a mapped drive, so the
   folder picker would not show it and backups would fail.
   Decision: the `.exe` runs normally (`asInvoker`). Backups need no admin.
   When the user clicks Restore and the app is not admin, it explains why and
   restarts itself as administrator (Windows shows the normal UAC prompt), then
   opens straight to the Restore screen. To make the backup folder still
   reachable after elevation, the app stores mapped-drive folders as their
   network path (`\\NAS\share\...`) using `to_unc_path()` (section 6.3).
   If the owner prefers "always admin", it is a one-word change in
   `build.bat` (add `--uac-admin`); everything else still works.
   *(This is open question Q1 in PLAN.md.)*

2. **Help opens inside the app, not as a .md file.** Many Windows PCs have no
   program set to open `.md` files, so double-clicking would show a confusing
   "How do you want to open this file?" box. The Help button shows
   `docs/QUICKSTART.md` (bundled into the .exe) in a simple read-only, scrollable
   window inside the app.

3. **Extra modules for testability.** Besides `backup_core.py`, `ui.py` and
   `main.py`, Windows-only code lives in `winutils.py`, settings/logging in
   `settings.py`, and each screen in its own `ui_*.py` file. Each file stays
   small enough for a small model to write in one step, and parallel steps
   never edit the same file.

4. **One-file .exe and antivirus.** PyInstaller one-file .exes are sometimes
   flagged by antivirus or SmartScreen because they are unsigned and unpack
   themselves. We keep one-file (simplest for users) and document the warning in
   TROUBLESHOOTING.md. We add Windows version info to the .exe, which helps a
   little.

---

## 3. File and folder layout

```
<repo root>/
  README.md
  LICENSE                     MIT
  SPEC.md                     this file
  PLAN.md                     build steps
  .gitignore
  build.bat                   one-command build
  requirements-dev.txt        pyinstaller (developer only)
  version_info.txt            Windows .exe version resource for PyInstaller
  src/
    main.py                   entry point; arg parsing; DPI; crash handler
    version.py                constants: name, version, license, disclaimer
    settings.py               settings file, log file, resource paths
    backup_core.py            ALL file logic; no UI, no Windows API calls
    winutils.py               Windows-only: processes, registry, admin, UNC
    ui.py                     App window, screen switching, home screen
    ui_widgets.py             shared widgets, fonts, status bar, background tasks
    ui_firstrun.py            "Is this correct?" screen
    ui_backup.py              backup screen
    ui_restore.py             restore step 1: pick a backup
    ui_restore_select.py      restore step 2: pick profiles, confirm, run
    ui_settings.py            settings screen
    ui_help.py                help viewer + About box
  tests/
    helpers.py                fake install / temp folder helpers
    test_settings.py
    test_core_basics.py
    test_core_backup.py
    test_core_list.py
    test_core_restore.py
    test_winutils.py
    test_ui_smoke.py
  tools/
    make_fake_install.py      creates a fake Afterburner folder for manual testing
    privacy_scan.py           scans repo for personal data patterns
  docs/
    QUICKSTART.md
    FAQ.md
    TROUBLESHOOTING.md
    DEVELOPER.md
```

Rules:
- All `src/*.py` modules import each other by plain name (`import backup_core`),
  because `src/` is on `sys.path` (PyInstaller `--paths src`; tests add it).
- `backup_core.py` must not import `tkinter`, `winreg`, `ctypes`, or any `ui*`.
- Screen modules are imported lazily, so PyInstaller cannot see them: `build.bat` must pass
  `--hidden-import <module>` for every `ui_*` screen module in `SCREENS`.
- `ui*.py` must not open, copy, or hash files themselves; they call
  `backup_core`, `winutils`, and `settings`. (Exception: `ui_help.py` reads the
  help text via `settings.read_help_text()`.)
- `winutils.py` must import on non-Windows too (guard `winreg`/`ctypes.windll`
  use inside functions, return safe defaults) so tests can import it anywhere.
- Every module starts with a short docstring saying what it is for.
- Type hints on every public function. Max line length 100.

---

## 4. Afterburner facts the app relies on

- Install folder default: `C:\Program Files (x86)\MSI Afterburner`
  (sometimes `C:\Program Files\MSI Afterburner`). Resolve `Program Files`
  paths with environment variables `ProgramFiles(x86)` and `ProgramFiles`,
  falling back to the literal paths only if the variables are missing.
- Process name: `MSIAfterburner.exe`.
- Profiles live in `<install>\Profiles\`. Files there end in `.cfg`, for
  example `Profile1.cfg`..`Profile5.cfg` and GPU-specific files like
  `VEN_10DE&DEV_2684&SUBSYS_...&BUS_1&DEV_0&FN_0.cfg`. Back up **every**
  `*.cfg` file in `Profiles\` (not subfolders).
- Main settings file: `<install>\MSIAfterburner.cfg` (optional, included by
  default; the user can switch it off in Settings).
- A folder counts as a valid install if it contains a `Profiles` subfolder.
- Afterburner usually runs as administrator, so closing it needs admin rights.
- Afterburner may rewrite its files when it exits, which is why it must be
  closed before a restore.
- GPU-specific profiles (`VEN_...`) only apply to the same graphics card in the
  same slot. Docs must mention this.

---

## 5. Data formats

### 5.1 Relative paths ("rel_path")

Every profile file is identified by a relative path using forward slashes:
- `MSIAfterburner.cfg` — main settings file in the install root, or
- `Profiles/<name>.cfg` — a file in the Profiles folder.

No other rel_path is ever valid. `backup_core.is_safe_rel_path()` enforces
this (protects against a tampered manifest writing elsewhere).

### 5.2 Backup folder layout

The user chooses a **backup folder** ("backup root"). Inside it:

```
<backup root>/
  2026-10-18_14-03-22/              one normal backup
    manifest.json
    MSIAfterburner.cfg              (if included)
    Profiles/
      Profile1.cfg
      VEN_....cfg
  2026-10-18_14-03-22_2/            same second → suffix _2, _3, ...
  before-restore/
    2026-10-19_09-00-00/            automatic safety copy made before a restore
      manifest.json
      ...
```

Folder name format: `YYYY-MM-DD_HH-MM-SS` in **local time**
(`datetime.strftime("%Y-%m-%d_%H-%M-%S")`).

### 5.3 manifest.json

UTF-8, indent 2, written **after** all files are copied and verified.

```json
{
  "app": "Afterburner Profile Backup",
  "app_version": "1.0.0",
  "manifest_version": 1,
  "kind": "backup",
  "created_local": "2026-10-18T14:03:22",
  "source_dir": "C:\\Program Files (x86)\\MSI Afterburner",
  "files": [
    {"rel_path": "Profiles/Profile1.cfg", "size": 1234, "sha256": "ab12...ef"}
  ]
}
```

- `kind` is `"backup"` or `"before-restore"`.
- `sha256` is lowercase hex.
- `created_local` is ISO format, seconds precision, no timezone.

### 5.4 settings.json

Location: `%LOCALAPPDATA%\AfterburnerProfileBackup\settings.json`
(if `LOCALAPPDATA` is not set, use `os.path.expanduser("~")` +
`\AppData\Local\AfterburnerProfileBackup`). Environment variable
`ABPB_SETTINGS_DIR` overrides the folder (used by tests).

```json
{
  "install_dir": "C:\\Program Files (x86)\\MSI Afterburner",
  "install_confirmed": true,
  "backup_root": "\\\\NAS\\share\\AfterburnerBackups",
  "include_main_cfg": true
}
```

Unknown keys are ignored. Missing/corrupt file → defaults (and log it).
"Test run" mode is **never** saved; it always starts off.

### 5.5 Log file

`<settings dir>\log.txt`, UTF-8, one line per event:
`2026-10-18 14:03:22 INFO Backed up 7 files to ...`. When the file exceeds
1,000,000 bytes, rename it to `log.old.txt` (replacing any older one) and start
a new file. Never log file contents.

---

## 6. Module interfaces (exact signatures)

All paths are `str`. All functions that touch the disk must catch `OSError`
and turn it into a plain-language result instead of raising, **unless** the
signature says it raises.

### 6.1 `src/version.py`

```python
APP_NAME: str = "Afterburner Profile Backup"
APP_ID: str = "AfterburnerProfileBackup"      # folder/exe name, no spaces
VERSION: str = "1.0.0"
LICENSE_NAME: str = "MIT License"
REPO_URL: str = "https://github.com/DroptheHammer/Afterburner_Profile_Backup"  # shown as text in About
DISCLAIMER: str  # exact text in section 11.3
```

### 6.2 `src/settings.py`

```python
@dataclass
class Settings:
    install_dir: str | None = None
    install_confirmed: bool = False
    backup_root: str | None = None
    include_main_cfg: bool = True

def settings_dir() -> str
    """Folder for settings and log. Creates it if missing. Honors ABPB_SETTINGS_DIR."""

def load_settings() -> Settings
    """Never raises. Missing or broken file -> Settings() defaults."""

def save_settings(s: Settings) -> bool
    """Writes settings.json atomically (write .tmp then os.replace). True on success."""

def log(level: str, message: str) -> None
    """level is "INFO", "WARN" or "ERROR". Never raises. Rotates at 1,000,000 bytes."""

def log_path() -> str

def resource_path(rel: str) -> str
    """Path to a bundled file. Uses sys._MEIPASS when frozen by PyInstaller,
    otherwise the repo root (parent of src/). rel uses forward slashes, e.g. "docs/QUICKSTART.md"."""

def read_help_text() -> str
    """Contents of docs/QUICKSTART.md, or a short friendly fallback text if missing."""
```

### 6.3 `src/winutils.py`

```python
AFTERBURNER_EXE: str = "MSIAfterburner.exe"

def is_windows() -> bool

def find_afterburner_process_paths() -> list[str]
    """Full paths of running MSIAfterburner.exe processes (case-insensitive match
    on the file name). Uses ctypes: psapi.EnumProcesses, kernel32.OpenProcess with
    PROCESS_QUERY_LIMITED_INFORMATION (0x1000), kernel32.QueryFullProcessImageNameW,
    kernel32.CloseHandle. Skips processes it cannot open. [] on non-Windows or error."""

def is_afterburner_running() -> bool
    """True if any process named MSIAfterburner.exe is running. Uses
    find_afterburner_process_paths(); if that returns [] also checks
    `tasklist /FI "IMAGENAME eq MSIAfterburner.exe" /NH` output (no window,
    see run_hidden). False on non-Windows."""

def registry_install_dirs() -> list[str]
    """Search HKLM SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall and
    HKLM SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall
    (also HKCU Uninstall) for subkeys whose DisplayName contains "MSI Afterburner"
    (case-insensitive). For each, take InstallLocation; if empty, take the folder of
    DisplayIcon or of UninstallString (strip quotes and any ",0" suffix / arguments).
    Return existing folders, no duplicates, in that order. [] on non-Windows."""

def default_install_dirs() -> list[str]
    """[%ProgramFiles(x86)%\\MSI Afterburner, %ProgramFiles%\\MSI Afterburner]."""

def find_install_dir() -> tuple[str | None, str]
    """Returns (folder, how_found). Order:
      0. env ABPB_TEST_INSTALL_DIR if set and it has a Profiles subfolder -> "test"
      1. folder of each running MSIAfterburner.exe                       -> "running"
      2. registry_install_dirs()                                        -> "registry"
      3. default_install_dirs()                                         -> "default"
    The first candidate that contains a "Profiles" subfolder wins.
    Nothing found -> (None, "none")."""

def close_afterburner(force: bool = False, timeout_s: float = 8.0) -> tuple[bool, str]
    """Runs `taskkill /IM MSIAfterburner.exe` (adds /F when force) hidden, then polls
    is_afterburner_running() every 0.5 s up to timeout_s.
    Returns (True, "Afterburner is closed.") or (False, plain-language reason).
    If access is denied, reason says admin permission is needed."""

def is_admin() -> bool
    """ctypes.windll.shell32.IsUserAnAdmin(); False on error or non-Windows."""

def relaunch_as_admin(extra_args: list[str]) -> bool
    """ShellExecuteW(None, "runas", exe, params, None, 1). When frozen, exe is
    sys.executable and params is extra_args. When not frozen, exe is sys.executable
    (python) and params is the path of main.py followed by extra_args. Quote each
    argument. Returns True if ShellExecuteW returned > 32 (caller then closes the app).
    False if the user said No to UAC or on error."""

def to_unc_path(path: str) -> str
    """If path starts with a drive letter that is a mapped network drive, return the
    UNC form (\\\\server\\share\\rest) using mpr.WNetGetConnectionW. Otherwise return
    path unchanged. Never raises."""

def run_hidden(args: list[str], timeout_s: float = 15.0) -> tuple[int, str]
    """subprocess.run with creationflags=CREATE_NO_WINDOW (0x08000000), capture text
    output (stdout+stderr), errors="replace". Returns (returncode, output).
    On exception returns (-1, str(exception))."""
```

### 6.4 `src/backup_core.py`

```python
MAIN_CFG_NAME: str = "MSIAfterburner.cfg"
PROFILES_DIR_NAME: str = "Profiles"
MANIFEST_NAME: str = "manifest.json"
BEFORE_RESTORE_DIR_NAME: str = "before-restore"
TEMP_SUFFIX: str = ".abpb-tmp"
FOLDER_TIME_FORMAT: str = "%Y-%m-%d_%H-%M-%S"

@dataclass(frozen=True)
class ProfileFile:
    rel_path: str        # see 5.1
    abs_path: str
    size: int            # bytes
    modified: float      # os.stat().st_mtime

@dataclass(frozen=True)
class FileRecord:
    rel_path: str
    size: int
    sha256: str

@dataclass
class BackupInfo:
    folder: str                  # absolute path of the backup folder
    kind: str                    # "backup" or "before-restore"
    created: datetime            # from manifest created_local; else parsed folder name; else mtime
    source_dir: str              # from manifest, "" if unknown
    files: list[FileRecord]      # from manifest; [] if manifest missing/broken
    manifest_ok: bool            # manifest present and readable

@dataclass
class OpResult:
    ok: bool
    message: str                 # one plain-language summary sentence for the status area
    details: list[str] = field(default_factory=list)   # one plain line per file/action
    folder: str | None = None    # backup folder created or used
    count: int = 0               # number of files backed up / restored (or that would be)
    dry_run: bool = False
    safety_folder: str | None = None   # restore only: the before-restore folder

# ---- basics (step 2) ----
def sha256_file(path: str) -> str
    """Lowercase hex SHA-256, reading in 1 MiB chunks. Raises OSError."""

def friendly_size(num_bytes: int) -> str
    """"512 bytes", "1.2 KB", "3.4 MB" (1 KB = 1024 bytes, one decimal for KB/MB)."""

def friendly_datetime(dt: datetime) -> str
    """e.g. "Sun 18 Oct 2026, 2:03 PM" -> format "%a %d %b %Y, %I:%M %p" with the
    leading zero of the hour removed."""

def count_text(n: int) -> str
    """"1 profile" or "<n> profiles". Use it in EVERY user message that shows a profile count
    (e.g. "Backed up 1 profile", "Restored 4 profiles", backup_label)."""

def make_backup_folder_name(now: datetime) -> str
    """now.strftime(FOLDER_TIME_FORMAT)."""

def parse_backup_folder_name(name: str) -> datetime | None
    """Inverse of the above. Accepts an optional "_<digits>" suffix. None if no match."""

def is_safe_rel_path(rel_path: str) -> bool
    """True only for "MSIAfterburner.cfg" or "Profiles/<name>" where <name> ends in .cfg
    (case-insensitive), has no "/" or "\\" and is not "." or "..". """

def is_valid_install_dir(path: str | None) -> bool
    """True if path is a folder containing a Profiles subfolder."""

def list_profile_files(install_dir: str, include_main_cfg: bool = True) -> list[ProfileFile]
    """All *.cfg files directly in <install>/Profiles (sorted by name, case-insensitive),
    then MSIAfterburner.cfg from the install root if include_main_cfg and it exists.
    [] if the folder is missing or unreadable."""

def check_folder_writable(folder: str) -> tuple[bool, str]
    """Checks folder exists (does NOT create it), is a folder, and a small test file
    ".abpb-write-test" can be created and removed. Returns (True, "") or
    (False, plain message). Messages:
      missing  -> "We can't reach this folder. If it is on a network drive or NAS, make sure
                   it is turned on and connected, then try again."
      not dir  -> "This is a file, not a folder. Please pick a folder."
      no write -> "We can't save files in this folder. Pick a different folder or check
                   that you have permission to save there." """

# ---- backup (step 4) ----
def write_manifest(folder: str, kind: str, source_dir: str, records: list[FileRecord],
                   now: datetime) -> None
    """Writes manifest.json (section 5.3). Raises OSError."""

def read_manifest(folder: str) -> dict | None
    """Parsed manifest dict, or None if missing, unreadable, invalid JSON, or missing the
    "files" list. Drops any file entry whose rel_path fails is_safe_rel_path()."""

def unique_backup_folder(parent: str, now: datetime) -> str
    """Absolute path <parent>/<name> that does not exist yet, adding _2, _3 ... if needed.
    Does not create it."""

def copy_verified(src: str, dst: str) -> tuple[int, str]
    """Copies src to dst + TEMP_SUFFIX with shutil.copy2, hashes both, and if equal
    os.replace()s the temp file onto dst. Creates dst's parent folder. Returns
    (size, sha256). Raises OSError on failure, or ValueError("verify failed") if hashes
    differ (temp file is left in place; never delete user files)."""

def create_backup(install_dir: str, backup_root: str, include_main_cfg: bool = True,
                  dry_run: bool = False, kind: str = "backup",
                  now: datetime | None = None) -> OpResult
    """1. files = list_profile_files(); none -> ok=False,
          message "We didn't find any profiles to back up in <install_dir>."
       2. parent = backup_root, or backup_root/before-restore when kind=="before-restore".
       3. check_folder_writable(backup_root) (create the before-restore parent first if
          needed); failure -> ok=False with that message.
       4. folder = unique_backup_folder(parent, now or datetime.now()).
       5. dry_run -> no writes; details "Would copy <rel_path> (<friendly size>)";
          message "Test run: would back up N profiles to <folder>. Nothing was changed."
       6. else copy each file with copy_verified into folder/<rel_path>; write manifest;
          message "Backed up N profiles to <folder>. Verified OK."
       Any error -> ok=False, message "The backup did not finish: <plain reason>.
       Your original profiles were not changed." (Files already copied are left.)"""

# ---- list (step 5) ----
def list_backups(backup_root: str) -> list[BackupInfo]
    """Every subfolder of backup_root whose name parses with parse_backup_folder_name OR
    that contains manifest.json, plus the same inside backup_root/before-restore
    (kind "before-restore"). Newest first by created. [] if root unreachable."""

def verify_backup(info: BackupInfo, rel_paths: list[str] | None = None) -> tuple[bool, list[str]]
    """Checks each selected file (default: all in info.files) exists in the backup folder
    and matches its size and sha256. Returns (all_ok, problems) where problems are plain
    lines like "Profile1.cfg is missing from the backup." or
    "Profile1.cfg in the backup is damaged (it doesn't match the original)." """

def backup_label(info: BackupInfo) -> str
    """"Sun 18 Oct 2026, 2:03 PM — 7 profiles" ; before-restore kind appends
    " (automatic safety copy made before a restore)"; manifest_ok False appends
    " (details missing — can't be checked)"."""

# ---- restore (step 6) ----
def target_path_for(install_dir: str, rel_path: str) -> str
    """Absolute destination of rel_path inside install_dir. Raises ValueError if
    rel_path is not safe."""

def restore_files(info: BackupInfo, rel_paths: list[str], install_dir: str,
                  backup_root: str, include_main_cfg: bool = True, dry_run: bool = False,
                  now: datetime | None = None) -> OpResult
    """1. rel_paths empty -> ok=False "Please pick at least one profile to restore."
       2. every rel_path must be safe and listed in info.files, else ok=False.
       3. verify_backup(info, rel_paths); problems -> ok=False, message
          "This backup can't be used safely: <first problem>", details = problems.
       4. check_folder_writable(install_dir) (skip when dry_run); failure -> ok=False
          message "We can't write to the Afterburner folder. Restoring needs
          administrator permission." 
       5. Safety copy: create_backup(install_dir, backup_root,
          include_main_cfg or MSIAfterburner.cfg is in rel_paths,
          dry_run, kind="before-restore", now). If it fails AND there were current
          profiles -> ok=False "We couldn't make a safety copy of your current
          profiles, so nothing was restored: <reason>". (No current profiles -> continue.)
       6. dry_run -> details "Would replace <rel_path>" or "Would add <rel_path>";
          message "Test run: would restore N profiles. Nothing was changed."
       7. else copy_verified(backup file -> target_path_for(...)) for each file.
          message "Restored N profiles. Verified OK. Please open Afterburner again."
          safety_folder = the before-restore folder.
       Error mid-way -> ok=False, message "The restore did not finish: <reason>.
       A safety copy of your previous profiles is in <safety folder>.",
       details lists what was and wasn't restored."""
```

---

## 7. UI framework rules (`ui_widgets.py`, `ui.py`)

### 7.1 Look and accessibility

- Window title: `Afterburner Profile Backup`. Minimum size 720x560, starts at
  900x680, resizable; content reflows (use `grid`/`pack` with `fill`/`expand`;
  long text labels use `wraplength` updated on resize).
- Fonts: named fonts created once in `ui_widgets.setup_fonts(root)`:
  `"ABPB.Body"` Segoe UI 12, `"ABPB.Hint"` Segoe UI 10, `"ABPB.Title"` Segoe UI 18 bold,
  `"ABPB.Big"` Segoe UI 16 bold (big buttons). Fall back to TkDefaultFont family
  if Segoe UI is unavailable.
- Use `ttk` with the default Windows theme (`vista` if available) so Windows
  high-contrast mode is respected. Do not hard-code background colors on
  frames. Color is only used for status text: success `#1b5e20` (green),
  problem `#b71c1c` (red), info default text color. Every status message also
  starts with a text marker so color is never the only signal:
  `"✔ Done: "`, `"✖ Problem: "`, `"ℹ "`, `"⚠ Warning: "`.
- Every button and input has a visible text label and a one-line hint label
  (`ABPB.Hint` font) directly beneath it.
- Keyboard: Tab/Shift+Tab move focus (default order = layout order); Enter
  activates the focused button (bind `<Return>` on ttk.Button to `invoke`);
  Esc goes back to the previous screen (on home screen Esc does nothing);
  Alt-key underlines are optional. Initial focus on each screen goes to its
  main button.
- Wording: say "profiles" (not cfg files), "folder" (not directory/path),
  "copy" / "safety copy", "Afterburner". No error codes or stack traces in the
  UI (they go to the log).

### 7.2 Background work

NAS copies can be slow; the window must never freeze.
`ui_widgets.run_background(root, func, on_done)` runs `func()` in a
`threading.Thread(daemon=True)`, polls with `root.after(100, ...)`, and calls
`on_done(result, error)` on the Tk thread (`error` is the exception or None).
While running, the screen disables its buttons and the status shows
`"ℹ Working… please wait."`. Tk widgets are touched only on the Tk thread.

### 7.3 `ui_widgets.py` interface

```python
SUCCESS_COLOR = "#1b5e20"; ERROR_COLOR = "#b71c1c"

def setup_fonts(root: tk.Tk) -> None
def big_button(parent, text: str, hint: str, command) -> ttk.Button
    """Creates a ttk.Frame inside parent holding a large button (style "Big.TButton",
    font ABPB.Big, padding 16) with the hint label under it. Does NOT place the frame.
    Returns the button; the caller places the frame with button.master.pack(...)/grid(...)."""
def small_button(parent, text: str, hint: str, command) -> ttk.Button
    """Same as big_button but normal size (font ABPB.Body). Caller places button.master."""
def labeled_hint(parent, text: str) -> ttk.Label        # hint label, wraps
def title_label(parent, text: str) -> ttk.Label
def body_label(parent, text: str) -> ttk.Label          # wraps

class StatusBar(ttk.Frame):
    """Bottom message area, always visible. Selectable read-only text so users can copy it."""
    def set(self, kind: str, text: str) -> None   # kind: "success" | "error" | "info" | "warning"
    def get_text(self) -> str

def run_background(root: tk.Misc, func, on_done) -> None

def confirm(parent, title: str, message: str, yes_text: str = "Yes", no_text: str = "No",
            default_no: bool = False) -> bool
    """Modal tk.Toplevel (transient, grab_set) with the message and two clearly labeled
    buttons. Enter activates the focused button, Esc = No, closing the window = No.
    Initial focus is on the Yes button, or on No when default_no is True (use
    default_no=True for anything that overwrites files). Returns True only for Yes."""

def show_info(parent, title: str, message: str) -> None   # modal, one "OK" button
def show_error(parent, title: str, message: str) -> None  # modal, one "OK" button, ✖ marker
def pick_folder(parent, title: str, initial: str | None) -> str | None
    """tkinter.filedialog.askdirectory(mustexist=True). Returns normalized path
    (os.path.normpath) or None if cancelled."""
```

### 7.4 `ui.py` interface

```python
class Screen(ttk.Frame):
    """Base class for screens. Subclasses implement build() and may override on_show()."""
    title: str = ""
    def __init__(self, app: "App", **kwargs): ...   # stores app, kwargs; calls build()
    def build(self) -> None: ...
    def on_show(self) -> None: ...                    # set initial focus here
    def busy(self, is_busy: bool) -> None: ...        # disable/enable all ttk.Buttons/Checkbuttons in self

class App(tk.Tk):
    settings: settings.Settings
    test_run: tk.BooleanVar          # "Test run (don't change anything)", starts False
    status: ui_widgets.StatusBar
    def __init__(self, start_screen: str = "home", test_run: bool = False): ...  # sets self.test_run
    def show_screen(self, name: str, **kwargs) -> None
        """Destroys current screen frame, creates the new one with kwargs, pushes name on a
        history stack. Unknown/missing module -> placeholder screen saying
        "This part of the app isn't built yet." """
    def go_back(self) -> None        # pops history; home if empty
    def go_home(self) -> None        # clears history, shows home
    def save_settings(self) -> None  # settings.save_settings(self.settings); error -> status error

SCREENS: dict[str, tuple[str, str]] = {
    "home":           ("ui", "HomeScreen"),
    "firstrun":       ("ui_firstrun", "FirstRunScreen"),
    "backup":         ("ui_backup", "BackupScreen"),
    "restore":        ("ui_restore", "RestoreScreen"),
    "restore_select": ("ui_restore_select", "RestoreSelectScreen"),
    "settings":       ("ui_settings", "SettingsScreen"),
    "help":           ("ui_help", "HelpScreen"),
}
# show_screen imports the module lazily with importlib.import_module and getattr.
# Screen modules do `from ui import Screen` (lazy import avoids circular import problems).

def run_app(start_screen: str = "home", selftest: bool = False, test_run: bool = False) -> int
    """Creates App. If selftest: for every SCREENS entry call show_screen(name) inside
    try/except, record failures, destroy the window, print one line per screen
    ("OK home" / "FAIL backup: <error>") and return 0 if all OK else 1. A screen that
    shows the placeholder counts as FAIL (its module is missing from the build). Screens must
    therefore build without user action and without dialogs when settings are empty
    (selftest passes dummy kwargs: restore_select gets backup=None and must show a
    friendly "Please pick a backup first" message).
    Otherwise run mainloop() and return 0."""
```

Startup logic in `App.__init__` (after building window):
1. `self.settings = settings.load_settings()`.
2. If `start_screen == "home"` and (`not settings.install_confirmed` or
   `not backup_core.is_valid_install_dir(settings.install_dir)`) → show
   `"firstrun"`; else show `start_screen`.

### 7.5 `main.py`

- Parse `sys.argv` with `argparse`: `--restore` (start on restore screen),
  `--test-run` (start with `app.test_run` ticked; used when relaunching as admin),
  `--selftest-ui` (run `run_app(selftest=True)` and `sys.exit` its code).
- On Windows call `ctypes.windll.shcore.SetProcessDpiAwareness(1)` in a
  try/except (crisp text on high-DPI screens).
- Install `sys.excepthook` and `tk.Tk.report_callback_exception` handlers that
  `settings.log("ERROR", traceback)` and show
  `"Something went wrong. Nothing was deleted. Details were saved to <log path>."`.
- `if __name__ == "__main__": sys.exit(main())`.

---

## 8. Screens (exact wording)

Text in quotes is the exact UI text. `[hint]` = one-line hint label under the
control. All screens show a "Back" button (top-left, hint-free) except Home.

### 8.1 Home (`ui.HomeScreen`)

- Title: "Afterburner Profile Backup"
- Body: "Keep a safe copy of your MSI Afterburner profiles, and put them back
  when you need them."
- Big button "Back Up My Profiles" [hint: "Copies your current profiles to
  your backup folder. Nothing is changed in Afterburner."] → `show_screen("backup")`
- Big button "Restore Profiles" [hint: "Puts profiles from an earlier backup
  back into Afterburner."] → restore flow (see 8.4 admin check), then
  `show_screen("restore")`.
- Checkbutton "Test run (don't change anything)" bound to `app.test_run`
  [hint: "Shows exactly what would happen, without copying anything."]
- Small buttons in a row: "Settings" [hint: "Change folders and options."],
  "Help" [hint: "Step-by-step guide."], "About" [hint: "Version and license."]
  (About calls `ui_help.show_about(app)`).
- Below: body label showing "Afterburner folder: <path>" and
  "Backup folder: <path or 'not chosen yet'>".
- Initial focus: "Back Up My Profiles". Status on first show:
  "ℹ Ready. Choose Back Up or Restore."

### 8.2 First run (`ui_firstrun.FirstRunScreen`)

On build: call `winutils.find_install_dir()` via `run_background`.
- Found: Title "We found your Afterburner profiles here. Is this correct?",
  the folder path in body text, then a `ttk.Treeview` (columns "Name",
  "Size", "Last changed"; Name shows file name only; Size via `friendly_size`;
  date via `friendly_datetime`) listing `list_profile_files(folder, True)`.
  Buttons: "Yes, that's right" [hint: "Use this folder."] and
  "No, let me pick the folder" [hint: "Choose the MSI Afterburner folder
  yourself. It is usually in Program Files (x86)."].
- Not found: Title "We couldn't find MSI Afterburner automatically." body
  "Please show us where it is installed. It is usually
  C:\Program Files (x86)\MSI Afterburner." Only the pick-folder button.
- Yes → `settings.install_dir = folder; install_confirmed = True;
  app.save_settings(); app.go_home()`; status success
  "✔ Done: Afterburner folder saved."
- Pick → `pick_folder`; if `is_valid_install_dir` → refresh the list with the
  new folder and ask again (same screen, same title); else
  `show_error(... "That folder doesn't look like MSI Afterburner. It should
  contain a folder named Profiles.")`.

### 8.3 Backup (`ui_backup.BackupScreen`)

- Title "Back Up My Profiles"
- Shows "Afterburner folder: <path>" and the number of profiles found
  ("We found 7 profiles to back up.").
- Row: label "Backup folder:" + read-only entry showing `settings.backup_root`
  + button "Choose Folder…" [hint: "Pick where to keep your backups — for
  example a folder on another drive or your NAS."]
- When a folder is picked: `path = winutils.to_unc_path(picked)`;
  `check_folder_writable(path)` (background); fail → status error with that
  message (do not save); ok → save to settings, status info "ℹ Backup folder
  saved."
- Shows "Test run is ON — nothing will be copied." in bold when
  `app.test_run` is true.
- Big button "Start Backup" [hint: "Makes a new dated folder inside your
  backup folder and copies your profiles into it."]. Disabled until a backup
  folder is set. Runs `create_backup(install_dir, backup_root,
  include_main_cfg, dry_run=app.test_run.get())` in the background.
- Result: status `success`/`error` with `result.message`; `details` shown in
  a scrollable read-only Text below the button. On success also a button
  "Open Backup Folder" [hint: "Shows the new backup in File Explorer."] which
  calls `os.startfile(result.folder)` (only when not dry run).

### 8.4 Restore — admin check (in `ui.HomeScreen` before showing restore)

If `winutils.is_windows()` and not `winutils.is_admin()`:
`confirm(app, "Administrator permission needed",
"Restoring puts files back into the MSI Afterburner folder, which Windows
protects. Windows will now ask for permission. Click Yes in that window to
continue.", yes_text="Continue", no_text="Cancel")`.
Continue → `winutils.relaunch_as_admin(["--restore"] + (["--test-run"] if app.test_run.get() else []))`; True → `app.destroy()`;
False → status error "✖ Problem: Windows permission was not given, so we can't
restore. You can still make backups." Running as admin (or not Windows) →
`show_screen("restore")` directly.

### 8.5 Restore step 1 (`ui_restore.RestoreScreen`)

- Title "Restore Profiles — Step 1 of 2: Pick a backup"
- Shows "Backup folder: <path>" + "Choose a Different Folder…" button
  [hint: "Use this if your backups are somewhere else."] (picked folder is
  converted with `to_unc_path` and saved).
- Listbox (single select, height ~10, scrollbar) filled from
  `list_backups(backup_root)` (background) using `backup_label()`.
  Newest first. Double-click or Enter = Next.
- Empty: body "No backups were found in this folder. Make a backup first, or
  choose the folder where your backups are."
- Button "Next" [hint: "See the profiles in this backup and choose which to
  put back."] → `show_screen("restore_select", backup=<BackupInfo>)`.
  Disabled until something is selected.

### 8.6 Restore step 2 (`ui_restore_select.RestoreSelectScreen`)

kwargs: `backup: BackupInfo | None`.
- Title "Restore Profiles — Step 2 of 2: Choose profiles"
- Body: "From the backup made on <friendly date>."
- Scrollable list of `ttk.Checkbutton`s, one per `FileRecord`, all ticked by
  default. Label = file name (+ " (main Afterburner settings)" for
  MSIAfterburner.cfg) + "  —  " + friendly size.
- Buttons "Select All" and "Select None" [one shared hint: "Tick the
  profiles you want to put back."]
- Warning label (always shown, ⚠ marker): "If Afterburner is set to apply
  settings when Windows starts, a restored profile may be applied the next
  time you start your PC."
- Big button "Restore Selected Profiles" [hint: "We'll make a safety copy of
  your current profiles first."]
- Flow when clicked:
  1. Nothing ticked → status error "Please pick at least one profile to restore."
  2. If `winutils.is_afterburner_running()` and not test run: confirm
     "Afterburner is still open", "MSI Afterburner is running. It needs to be
     closed first, otherwise it may overwrite the restored profiles when it
     closes.\n\nShall we close Afterburner for you?",
     yes_text="Close Afterburner for me", no_text="I'll close it myself".
     Yes → `close_afterburner()` (background); fail → confirm "Afterburner
     didn't close", "<reason>\n\nForce it to close?", "Force close", "Cancel"
     → `close_afterburner(force=True)`; still failing → status error, stop.
     No → status info "ℹ Please close Afterburner (right-click its icon near
     the clock and choose Exit), then click Restore again." stop.
  3. Confirmation summary: `confirm(... "Restore these profiles?",
     "We will:\n1. Make a safety copy of your current profiles in
     <backup_root>\\before-restore.\n2. Replace <N> profiles in <install_dir>
     with the ones from <friendly date>:\n   • name\n   • …\n\nThis changes
     your Afterburner settings. Continue?", yes_text="Yes, restore",
     no_text="Cancel", default_no=True)`. In test run the title is
     "Test run — nothing will change" and yes_text "Show me".
  4. Run `restore_files(...)` in the background; show result like backup
     screen (status + details). Success (not test run) → `show_info("Restore
     finished", "Your profiles were restored and checked.\n\nPlease open MSI
     Afterburner again. If it is set to apply settings when Windows starts,
     the restored profile may apply next time you start your PC.")`.
- `backup is None` → body "Please pick a backup first." + Back button only.

### 8.7 Settings (`ui_settings.SettingsScreen`)

- "Afterburner folder: <path>" + "Change…" [hint: "Only change this if we
  found the wrong folder."] → pick, validate with `is_valid_install_dir`, save.
- "Find it again automatically" [hint: "Search for MSI Afterburner again."]
  → `show_screen("firstrun")`.
- "Backup folder: <path>" + "Change…" [hint: "Where your backups are saved."]
  (same logic as backup screen).
- Checkbutton "Also back up the main Afterburner settings file" bound to
  `include_main_cfg` [hint: "Recommended. This file holds Afterburner's
  general options (MSIAfterburner.cfg)."] — saved on change.
- Button "Open Log File" [hint: "For troubleshooting. Shows what the app
  did."] → `os.startfile(settings.log_path())` if it exists, else info
  "There is no log yet."

### 8.8 Help (`ui_help.HelpScreen`) and About

- HelpScreen: title "Help", read-only scrollable `tk.Text` (font ABPB.Body,
  wrap word) filled with `settings.read_help_text()`. Simple rendering: lines
  starting with `#` shown with ALL leading `#` characters and following spaces removed, using a bold tag; other
  Markdown left as plain text. Text widget is focusable so arrow keys / Page
  Down scroll.
- `show_about(app) -> None`: `show_info(app, "About", f"{APP_NAME}\nVersion
  {VERSION}\n{LICENSE_NAME}\n\n{DISCLAIMER}\n\nNo data ever leaves your PC.\n\n
  Updates and source code:\n{REPO_URL}")`.

---

## 9. Messages always go to the status bar

Rule: every action ends with a status update (success, error, or info) that
says what happened and what to do next. Errors also get `settings.log("ERROR",
...)`. Successes get `settings.log("INFO", ...)`.

---

## 10. Testing

- Tests never touch real Afterburner files or real settings. Each test sets
  `ABPB_SETTINGS_DIR` to a temp folder (in `setUp`, restored in `tearDown`).
- `tests/helpers.py`:
  ```python
  def add_src_to_path() -> None      # inserts <repo>/src at sys.path[0] once
  def make_fake_install(root: str, profile_names: list[str] | None = None,
                        with_main_cfg: bool = True) -> str
      """Creates <root>/MSI Afterburner/Profiles with fake .cfg files (default names:
      "Profile1.cfg", "Profile2.cfg", "VEN_10DE&DEV_0000&SUBSYS_00000000&REV_A1&BUS_1&DEV_0&FN_0.cfg"),
      each containing "[Startup]\\nFormat=2\\n" plus its own name so hashes differ, and
      MSIAfterburner.cfg if with_main_cfg. Returns the install folder path."""
  ```
- UI smoke test: `tests/test_ui_smoke.py` runs `python src/main.py
  --selftest-ui` as a subprocess (timeout 60 s) and asserts exit code 0. Skip
  with `unittest.skip` if no display is available (`tkinter.TclError` on `tk.Tk()`).
- `tools/make_fake_install.py <folder>`: creates a fake install using the same
  layout and prints `set ABPB_TEST_INSTALL_DIR=<path>` for manual testing.

---

## 11. Documentation rules

### 11.1 Style

Short sentences. Numbered steps. No jargon. Screenshot placeholders exactly
like `[SCREENSHOT: Home screen with the two big buttons]`. Example paths use
placeholders only: `\\NAS\share\AfterburnerBackups`, `C:\Users\<you>\...`,
`D:\Backups\Afterburner`.

### 11.2 Required docs

- `README.md`: what it is, who it's for, download & run in 3 steps, safety
  notes, disclaimer (11.3), license, link to docs.
- `docs/QUICKSTART.md`: first backup; first restore; test run.
- `docs/FAQ.md`: Where are my profiles? Will this change my settings? Do I
  need to close Afterburner? Does it work with a NAS? Why does Restore ask for
  administrator permission? Will profiles work on a different graphics card?
  Where are settings and logs kept? Does it send any data?
- `docs/TROUBLESHOOTING.md`: can't find profiles; NAS not reachable (incl.
  mapped drive vs `\\server\share`); Windows SmartScreen "Windows protected
  your PC" and antivirus warnings on an unsigned .exe; restore didn't seem to
  apply (Afterburner was open, startup profile, different GPU); "can't write
  to Afterburner folder".
- `docs/DEVELOPER.md`: requirements, build with `build.bat`, layout, running
  tests, running from source, `ABPB_TEST_INSTALL_DIR`, `--selftest-ui`,
  privacy scan.

### 11.3 Disclaimer (exact text, used in README and `version.DISCLAIMER`)

"This app is not affiliated with or endorsed by MSI or the authors of MSI
Afterburner or RivaTuner. It only copies your own files and does not include
any part of Afterburner. Use it at your own risk, and test a restore before you
rely on it."

---

## 12. Privacy and open-source rules

- No usernames, computer names, NAS names/addresses/shares, IPs, emails,
  personal drive letters, or real profile files anywhere in the repo.
- Never hard-code a user folder; use `os.environ` (`LOCALAPPDATA`,
  `ProgramFiles`, `ProgramFiles(x86)`) or `os.path.expanduser`.
- `.gitignore` must cover: `*.cfg`, `settings.json`, `log.txt`, `log.old.txt`,
  `manifest.json`, backup folders (`[0-9][0-9][0-9][0-9]-[0-9][0-9]-*/`,
  `before-restore/`), `*.abpb-tmp`, `build/`, `dist/`, `*.spec`, `.venv/`,
  `__pycache__/`, `*.pyc`, `.claude/`, `*.log`.
- `tools/privacy_scan.py` (standard library only) walks the repo (skipping
  `.git`, `.venv`, `build`, `dist`, `__pycache__`) and reports lines matching:
  email addresses; IPv4 addresses (except 0.0.0.0/127.0.0.1 and version-like
  strings in `version_info.txt`); `C:\Users\<name>` where name is not
  `<you>`; UNC paths other than `\\NAS\share` / `\\server\share`; the current
  user's `USERNAME` and `COMPUTERNAME` env values (case-insensitive); any
  `.cfg` file present. Exit code 1 if anything found, prints file:line:reason.
