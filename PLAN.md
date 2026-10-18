# Afterburner Profile Backup — Build Plan

Read `SPEC.md` first. Every step below is meant to be given to a small model
together with `SPEC.md` and nothing else. Steps are small (about 150 lines of
code each, tests not counted unless stated).

## Open questions (answer before building)

- **Q1. Admin rights.** Recommended: the .exe runs normally and asks for
  admin only when you click Restore (keeps mapped NAS drives visible — see
  SPEC 2.1). Alternative: always run as admin, as in the original brief.
  Default if no answer: recommended option.
- **Q2. Copyright line in LICENSE.** MIT needs a holder name. Options: your
  GitHub username, or the neutral "Afterburner Profile Backup contributors".
  Default: "Afterburner Profile Backup contributors".
- **Q3. GitHub repo URL** shown in the About box. Default: leave the
  placeholder `https://github.com/<owner>/afterburner-profile-backup` and fill
  it in at publish time (step 21).

## How to hand a step to a small model

Prompt template:

> You are building one step of a project. Here is SPEC.md (the full spec) and
> step N from PLAN.md. Do only this step. Create/edit only the files listed.
> Use only names and signatures from SPEC.md. Stay under the size limit.
> When finished, run the acceptance test commands and show their output.

General rules for every step:
- Run from the repo root. Python launcher is `py` (or `python`).
- After every step, `py -m unittest discover -s tests -v` must pass (tests for
  steps not built yet do not exist yet, so this stays green).
- "Runnable" means: before step 6 the test suite passes; from step 6 on, the
  app also opens with `py src\main.py` and `py src\main.py --selftest-ui`
  prints only `OK` lines.
- Do not change files owned by other steps. If something in SPEC.md looks
  wrong, stop and report it instead of guessing.

## Dependency map and parallel waves

| Wave | Steps (can run in parallel inside a wave) | Needs |
|---|---|---|
| A | 1 | — |
| B | 2, 3, 4, 5, 17, 18, 19 | 1 |
| C | 6, 7 | 6 needs 2,3,4,5 · 7 needs 3 |
| D | 8, 10, 14, 15, 16 | 8 needs 7 · others need 6 |
| E | 9, 11, 12 | 9 needs 8 · 11 needs 6,7 · 12 needs 6,8 |
| F | 13 | 9, 12 |
| G | 20 (strong model) | all |
| H | 21 (strong model) | 20 |

No two steps in the same wave edit the same file.

---

## Step 1 — Project skeleton

- **Goal:** Create folders and the small fixed files every other step relies on.
- **Files to create:** `.gitignore`, `LICENSE`, `requirements-dev.txt`,
  `src/version.py`, `tests/__init__.py` (empty), `tests/helpers.py`,
  `docs/` (folder), `tools/` (folder; add `tools/.gitkeep` if empty).
- **Details:**
  - `.gitignore`: exactly the patterns in SPEC 12.
  - `LICENSE`: standard MIT text, year 2026, holder per Q2.
  - `requirements-dev.txt`: `pyinstaller>=6.16`.
  - `src/version.py`: constants in SPEC 6.1; `DISCLAIMER` = SPEC 11.3 text.
  - `tests/helpers.py`: `add_src_to_path()` and `make_fake_install()` per SPEC 10.
- **Inputs/outputs:** none / files above.
- **Acceptance test:**
  ```
  py -c "import sys; sys.path.insert(0,'src'); import version; print(version.APP_NAME, version.VERSION)"
  py -c "import tempfile,os,tests.helpers as h; d=h.make_fake_install(tempfile.mkdtemp()); print(sorted(os.listdir(os.path.join(d,'Profiles'))), os.path.exists(os.path.join(d,'MSIAfterburner.cfg')))"
  ```
  First prints `Afterburner Profile Backup 1.0.0`; second prints 3 `.cfg`
  names and `True`.
- **Size limit:** 80 lines of Python.

## Step 2 — Settings and log (`settings.py`)

- **Goal:** Load/save settings, write the log, find bundled files.
- **Parallel with:** 3, 4, 5, 17, 18, 19.
- **Files:** create `src/settings.py`, `tests/test_settings.py`.
- **Inputs/outputs:** SPEC 5.4, 5.5, 6.2.
- **Details:** atomic save (`.tmp` + `os.replace`); `load_settings` ignores
  unknown keys and wrong types (falls back to default per field); log
  rotation at 1,000,000 bytes; `resource_path` handles frozen and source runs;
  `read_help_text` fallback text: "The help file is missing. Please see
  README.md on the project page."
- **Acceptance test:** `py -m unittest tests.test_settings -v` passes, with
  tests that (using `ABPB_SETTINGS_DIR` = temp folder):
  1. load with no file → defaults;
  2. save then load → same values;
  3. corrupt JSON → defaults, no exception;
  4. `log()` writes a line containing the message and level;
  5. a log file over 1,000,000 bytes is renamed to `log.old.txt` on next log;
  6. `resource_path("docs/QUICKSTART.md")` ends with `docs\QUICKSTART.md`.
- **Size limit:** 120 lines (code), tests up to 100.

## Step 3 — Core basics (`backup_core.py`, part 1)

- **Goal:** Pure helper functions and profile discovery.
- **Parallel with:** 2, 4, 5, 17, 18, 19.
- **Files:** create `src/backup_core.py` (constants, the 4 dataclasses, and
  the "basics (step 2)" functions in SPEC 6.4); create `tests/test_core_basics.py`.
- **Inputs/outputs:** SPEC 5.1, 6.4 basics.
- **Acceptance test:** `py -m unittest tests.test_core_basics -v` passes, covering:
  - `sha256_file` of a file with `b"abc"` =
    `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`;
  - `friendly_size(512)=="512 bytes"`, `friendly_size(1536)=="1.5 KB"`,
    `friendly_size(3*1024*1024)=="3.0 MB"`;
  - `friendly_datetime(datetime(2026,10,18,14,3))=="Sun 18 Oct 2026, 2:03 PM"`;
  - folder name round-trip, including `"2026-10-18_14-03-22_2"`; `"hello"` → None;
  - `is_safe_rel_path`: True for `MSIAfterburner.cfg`, `Profiles/Profile1.cfg`;
    False for `../x.cfg`, `Profiles/../x.cfg`, `Profiles/a/b.cfg`,
    `Profiles/x.txt`, `C:/x.cfg`, `Profiles\\x.cfg`;
  - `list_profile_files` on a fake install → 4 files with main cfg, 3 without,
    profiles sorted, main cfg last; missing folder → `[]`;
  - `check_folder_writable`: temp folder → `(True, "")`; missing folder →
    False with the "can't reach" message; a file path → False.
- **Size limit:** 150 lines (code).

## Step 4 — Windows helpers (`winutils.py`)

- **Goal:** Find Afterburner, detect/close its process, admin, UNC paths.
- **Parallel with:** 2, 3, 5, 17, 18, 19.
- **Files:** create `src/winutils.py`, `tests/test_winutils.py`.
- **Inputs/outputs:** SPEC 4, 6.3.
- **Details:** import `winreg`/`ctypes.wintypes` inside functions or under
  `if sys.platform == "win32"`. Declare ctypes `argtypes`/`restype` for every
  API used. Must never raise from public functions (except none listed).
  Do NOT use PowerShell or `wmic`.
- **Acceptance test:** `py -m unittest tests.test_winutils -v` passes:
  - module imports; `is_windows()` matches `sys.platform == "win32"`;
  - `find_afterburner_process_paths()` returns a list (may be empty) and
    every item ends with `msiafterburner.exe` (case-insensitive);
  - with `ABPB_TEST_INSTALL_DIR` = a fake install, `find_install_dir()` →
    `(that folder, "test")`;
  - `to_unc_path(tempfile.gettempdir())` returns the same path;
  - `run_hidden(["cmd", "/c", "echo", "hi"])` → `(0, "hi...")` on Windows;
  - `is_admin()` returns a bool; `default_install_dirs()` has 2 entries.
  - Manual check (report output, don't fail on it):
    `py -c "import sys; sys.path.insert(0,'src'); import winutils as w; print(w.find_install_dir(), w.is_afterburner_running())"`
- **Size limit:** 160 lines (code).

## Step 5 — Shared UI widgets (`ui_widgets.py`)

- **Goal:** Fonts, buttons with hints, status bar, dialogs, background runner.
- **Parallel with:** 2, 3, 4, 17, 18, 19.
- **Files:** create `src/ui_widgets.py`.
- **Inputs/outputs:** SPEC 7.1, 7.2, 7.3.
- **Details:** `StatusBar` uses a read-only `tk.Text` (height 3, wrap word,
  state disabled between updates) with tags `success`/`error`/`warning`
  colored per SPEC and prefixes the marker text. Include
  `if __name__ == "__main__":` demo that opens a window with one big button,
  one small button, a status bar cycling all 4 kinds, and closes itself after
  3 seconds when run with `--auto-close`.
- **Acceptance test:**
  ```
  py src\ui_widgets.py --auto-close
  ```
  exits with code 0 within ~5 seconds and prints nothing to stderr. Also
  `py -c "import sys; sys.path.insert(0,'src'); import ui_widgets"` succeeds.
  Human check (optional): run without `--auto-close`, Tab between buttons,
  press Enter, check the status text starts with ✔ / ✖ / ℹ / ⚠.
- **Size limit:** 160 lines.

## Step 6 — App shell, home screen, entry point (`ui.py`, `main.py`)

- **Goal:** The app opens, shows Home, switches screens, self-tests.
- **Depends on:** 2, 3, 4, 5.
- **Files:** create `src/ui.py`, `src/main.py`, `tests/test_ui_smoke.py`.
- **Inputs/outputs:** SPEC 7.4, 7.5, 8.1, 8.4.
- **Details:** `SCREENS` lists all screens now; missing modules show the
  placeholder screen (so later steps only add their own file). Home screen
  wording exactly as SPEC 8.1. Restore button runs the admin check of 8.4.
  Esc binding on the App calls `go_back()` unless on home.
- **Acceptance test:**
  1. `py src\main.py --selftest-ui` prints `OK home` and, for not-yet-built
     screens, `OK <name>` (placeholder counts as OK); exit code 0.
  2. `py -m unittest tests.test_ui_smoke -v` passes.
  3. Human check: `py src\main.py` opens the window; first run shows the
     placeholder for "firstrun" (fine for now).
- **Size limit:** 170 lines total for both files.

## Step 7 — Core backup (`backup_core.py`, part 2)

- **Goal:** Make verified backups with a manifest.
- **Parallel with:** 6.
- **Depends on:** 3.
- **Files:** edit `src/backup_core.py` (append the "backup (step 4)"
  functions only); create `tests/test_core_backup.py`.
- **Inputs/outputs:** SPEC 5.2, 5.3, 6.4 backup.
- **Acceptance test:** `py -m unittest tests.test_core_backup -v` passes:
  - backup of a fake install → `ok`, `count==4`, folder name parses, files
    present under `Profiles/`, manifest has 4 entries with correct hashes,
    `kind=="backup"`;
  - two backups with the same `now` → second folder ends with `_2`;
  - `dry_run=True` → `ok`, `count==4`, folder does NOT exist, message starts
    with "Test run";
  - `kind="before-restore"` → folder is inside `<root>/before-restore`;
  - unreachable backup root → `ok False`, message contains "can't reach";
  - empty Profiles folder → `ok False`, message contains "didn't find";
  - `read_manifest` drops an entry with `rel_path` `"../evil.cfg"`;
  - original files unchanged after backup (same hashes).
- **Size limit:** 150 lines added.

## Step 8 — Core listing and verifying (`backup_core.py`, part 3)

- **Goal:** List backups newest-first and check them.
- **Parallel with:** 10, 14, 15, 16.
- **Depends on:** 7.
- **Files:** edit `src/backup_core.py` (append "list (step 5)" functions);
  create `tests/test_core_list.py`.
- **Inputs/outputs:** SPEC 6.4 list.
- **Acceptance test:** `py -m unittest tests.test_core_list -v` passes:
  - three backups made with `now` = day 1, day 3, day 2 plus one
    before-restore → `list_backups` returns 4, ordered day 3, day 2, …,
    kinds correct;
  - a random folder `"notes"` without manifest is ignored; a dated folder
    without manifest is listed with `manifest_ok False`;
  - `verify_backup` OK on fresh backup; after changing one byte of a backup
    file → False and the problem mentions "damaged"; after renaming one file
    → problem mentions "missing";
  - `backup_label` contains "4 profiles" and "safety copy" for before-restore;
  - missing root → `[]`.
- **Size limit:** 110 lines added.

## Step 9 — Core restore (`backup_core.py`, part 4)

- **Goal:** Restore selected files safely with a safety copy first.
- **Parallel with:** 11, 12.
- **Depends on:** 8.
- **Files:** edit `src/backup_core.py` (append "restore (step 6)"
  functions); create `tests/test_core_restore.py`.
- **Inputs/outputs:** SPEC 6.4 restore.
- **Acceptance test:** `py -m unittest tests.test_core_restore -v` passes:
  - back up fake install, modify `Profile1.cfg`, restore only
    `Profiles/Profile1.cfg` → `ok`, file content back to original,
    `Profile2.cfg` untouched, a before-restore folder exists containing the
    *modified* `Profile1.cfg`;
  - restore all → every file matches the backup hashes;
  - `dry_run` → nothing changes in install, no before-restore folder,
    details contain "Would replace";
  - a file deleted from install then restored → detail "Would add" in dry
    run and file present after real run;
  - empty selection → `ok False` "pick at least one";
  - rel_path not in backup → `ok False`;
  - damaged backup file → `ok False`, install untouched, message contains
    "can't be used safely";
  - `target_path_for(install, "../x.cfg")` raises `ValueError`.
- **Size limit:** 120 lines added.

## Step 10 — First-run screen (`ui_firstrun.py`)

- **Parallel with:** 8, 14, 15, 16. **Depends on:** 6.
- **Goal / spec:** SPEC 8.2.
- **Files:** create `src/ui_firstrun.py` only.
- **Acceptance test:**
  1. `py src\main.py --selftest-ui` shows `OK firstrun`, exit 0.
  2. Human check with a fake install:
     `py tools\make_fake_install.py %TEMP%\abpb-fake` (if step 16 is not done
     yet, use `py -c "import tempfile,tests.helpers as h; print(h.make_fake_install(r'%TEMP%\abpb-fake'))"`),
     then `set ABPB_TEST_INSTALL_DIR=<printed path>` and
     `set ABPB_SETTINGS_DIR=%TEMP%\abpb-settings`, run `py src\main.py`:
     the first-run screen lists 4 files; "Yes, that's right" returns to Home
     and the status says "✔ Done: Afterburner folder saved."
- **Size limit:** 130 lines.

## Step 11 — Backup screen (`ui_backup.py`)

- **Parallel with:** 9, 12. **Depends on:** 6, 7.
- **Goal / spec:** SPEC 8.3.
- **Files:** create `src/ui_backup.py` only.
- **Acceptance test:**
  1. `--selftest-ui` shows `OK backup`.
  2. Human check (fake install + temp settings as in step 10): choose a temp
     backup folder; Start Backup → status "✔ Done: Backed up 4 profiles to …
     Verified OK."; a dated folder with `manifest.json` exists; tick Test run
     on Home, back up again → status starts "Test run" and no new folder.
  3. Pick a non-existent network path (type `\\NAS\share` in the picker) →
     red "can't reach" message, nothing saved.
- **Size limit:** 150 lines.

## Step 12 — Restore step 1 screen (`ui_restore.py`)

- **Parallel with:** 9, 11. **Depends on:** 6, 8.
- **Goal / spec:** SPEC 8.5.
- **Files:** create `src/ui_restore.py` only.
- **Acceptance test:**
  1. `--selftest-ui` shows `OK restore`.
  2. Human check: with 2+ backups in the temp backup folder, start with
     `py src\main.py --restore` → list shows them newest first with dates and
     counts; selecting one enables Next; Next opens step 2 (placeholder until
     step 13).
- **Size limit:** 120 lines.

## Step 13 — Restore step 2 screen (`ui_restore_select.py`)

- **Depends on:** 9, 12.
- **Goal / spec:** SPEC 8.6.
- **Files:** create `src/ui_restore_select.py` only.
- **Acceptance test:**
  1. `--selftest-ui` shows `OK restore_select` (with `backup=None` it shows
     "Please pick a backup first.").
  2. Human check (run from an admin terminal or accept UAC): change
     `Profile1.cfg` in the fake install, restore just that profile → confirm
     dialog lists one name, result "✔ Done: Restored 1 profiles…", file
     content is back, `before-restore` folder created. Select None then
     Restore → red "Please pick at least one profile". Test run → summary
     only, no changes. (Optional, needs real Afterburner: running-process
     prompt appears and "Close Afterburner for me" closes it.)
- **Size limit:** 160 lines.

## Step 14 — Settings screen (`ui_settings.py`)

- **Parallel with:** 8, 10, 15, 16. **Depends on:** 6.
- **Goal / spec:** SPEC 8.7.
- **Files:** create `src/ui_settings.py` only.
- **Acceptance test:** `--selftest-ui` shows `OK settings`. Human check:
  untick "Also back up the main Afterburner settings file", restart app,
  it is still unticked (check `settings.json`); picking a folder without
  `Profiles` shows the friendly error.
- **Size limit:** 130 lines.

## Step 15 — Help screen and About (`ui_help.py`)

- **Parallel with:** 8, 10, 14, 16. **Depends on:** 6.
- **Goal / spec:** SPEC 8.8.
- **Files:** create `src/ui_help.py` only.
- **Acceptance test:** `--selftest-ui` shows `OK help`. Human check: Help
  shows QUICKSTART text with bold headings (or the fallback text if docs are
  not written yet); About shows version 1.0.0, "MIT License" and the
  disclaimer; Esc closes About and returns from Help.
- **Size limit:** 90 lines.

## Step 16 — Build script and fake-install tool

- **Parallel with:** 8, 10, 14, 15. **Depends on:** 6.
- **Files:** create `build.bat`, `version_info.txt`, `tools/make_fake_install.py`.
- **Details:**
  - `build.bat` (plain cmd, `@echo off`, `setlocal`, `cd /d "%~dp0"`):
    1. find Python: `py -3` else `python`; if neither, print "Python 3.10+
       is needed to BUILD (not to use) the app. Get it from python.org." and
       exit 1;
    2. create `.venv` if missing; `pip install -r requirements-dev.txt`;
    3. run unit tests; stop on failure;
    4. `pyinstaller --noconfirm --clean --onefile --windowed
       --name AfterburnerProfileBackup --paths src
       --add-data "docs\QUICKSTART.md;docs" --version-file version_info.txt
       src\main.py` (add `--uac-admin` only if Q1 = always admin);
    5. print the full path of `dist\AfterburnerProfileBackup.exe`; `pause`
       only when double-clicked (skip if `%1`==`nopause`).
    Every step checks `errorlevel` and prints a plain message on failure.
  - `version_info.txt`: PyInstaller `VSVersionInfo` with FileVersion/
    ProductVersion 1.0.0 (four-part form), ProductName "Afterburner Profile Backup",
    FileDescription same, LegalCopyright "MIT License", no company or person names.
  - `tools/make_fake_install.py`: SPEC 10.
- **Acceptance test:** `build.bat nopause` ends with the exe path; the exe
  exists; `dist\AfterburnerProfileBackup.exe --selftest-ui` returns exit
  code 0 (check with `echo %errorlevel%`); double-clicking the exe opens the
  window with no console window.
- **Size limit:** 120 lines total (excluding version_info boilerplate).

## Step 17 — Privacy scanner (`tools/privacy_scan.py`)

- **Parallel with:** wave B. **Depends on:** 1.
- **Goal / spec:** SPEC 12 scanner rules.
- **Files:** create `tools/privacy_scan.py`, `tests/test_privacy_scan.py`.
- **Acceptance test:** `py -m unittest tests.test_privacy_scan -v` passes:
  a temp folder with a file containing an email address, a private IPv4
  address and a user folder path with a real-looking name (build these test
  strings at run time so the repo scan stays clean) → 3 findings, exit code 1; a file
  with only `\\NAS\share\AfterburnerBackups` and `C:\Users\<you>\` → 0
  findings, exit code 0. Then `py tools\privacy_scan.py` on the repo
  reports its findings (report them; fixing is step 21).
- **Size limit:** 110 lines (code).

## Step 18 — User docs A: `README.md`, `docs/QUICKSTART.md`

- **Parallel with:** wave B. **Depends on:** SPEC only.
- **Goal / spec:** SPEC 8 (exact button names), 11.
- **Acceptance test (checklist, report each as pass/fail):**
  button names match SPEC 8 exactly; every step is numbered; at least one
  `[SCREENSHOT: …]` per major step; README has the exact disclaimer (11.3),
  license line, "download and run in 3 steps", safety notes (nothing deleted,
  safety copy before restore, test run); no real names/paths (only
  placeholders from 11.1); QUICKSTART under ~120 lines and starts with a
  `# ` heading (Help screen renders it).
- **Size limit:** README ≤ 100 lines, QUICKSTART ≤ 120 lines.

## Step 19 — User/dev docs B: `FAQ.md`, `TROUBLESHOOTING.md`, `DEVELOPER.md`

- **Parallel with:** wave B. **Depends on:** SPEC only.
- **Goal / spec:** SPEC 11.2 topics (all of them), plain language.
- **Acceptance test (checklist):** every FAQ question from SPEC 11.2 present
  as a heading; every troubleshooting topic present with numbered fixes;
  SmartScreen section says "More info" → "Run anyway" and explains why
  (unsigned, free app) and suggests checking the download came from the
  project's GitHub Releases page; DEVELOPER.md commands match `build.bat`,
  the test command, `--selftest-ui`, `ABPB_TEST_INSTALL_DIR`,
  `ABPB_SETTINGS_DIR`, `tools\privacy_scan.py`; no personal data.
- **Size limit:** each file ≤ 150 lines.

---

## Step 20 — Integration and review (strong model)

- **Goal:** Make sure all pieces fit, behave as SPEC says, and the .exe works.
- **Files:** any, but keep changes minimal and explain each.
- **Tasks:**
  1. Read all of `src/` against SPEC; list mismatches (names, wording,
     missing status messages, any UI module doing file work, any
     `backup_core` UI/Windows import). Fix them.
  2. Full test suite + `--selftest-ui` from source.
  3. End-to-end manual run with a fake install and a temp backup folder:
     first run → backup → test-run backup → change a profile → restore one
     (as admin via the real UAC relaunch from a non-admin start) → check
     before-restore copy → restore all → restore from the before-restore
     copy (undo). Keyboard-only pass (Tab/Enter/Esc) through every screen.
     Resize to minimum size; nothing cut off.
  4. Mapped drive / UNC: back up to a mapped drive letter (if available) or
     a share on this same PC (the admin share of drive C); confirm settings stores the UNC path
     and restore works after elevation.
  5. Error paths: unplugged/unknown network folder, read-only backup folder,
     damaged backup, Afterburner running (real or simulated by running a
     copied/renamed dummy exe named `MSIAfterburner.exe`).
  6. Build with `build.bat`, run the .exe on a clean user profile/VM if
     possible; confirm no console window, Help works inside the exe,
     settings/log written only to `%LOCALAPPDATA%\AfterburnerProfileBackup`.
  7. Check no network use: grep `src/` for `socket`, `urllib`, `http`,
     `requests` — none allowed.
- **Acceptance:** written report (in chat) of each task with pass/fail and
  what was fixed; all tests green; .exe built.

## Step 21 — Privacy scan and pre-publish (strong model)

- **Goal:** Nothing personal goes to GitHub.
- **Tasks:**
  1. Run `py tools\privacy_scan.py`; review every finding by hand.
  2. Manually check every file in the repo (list them) for: user names,
     computer names, emails, NAS names/shares/IPs, personal drive letters or
     folders, real `.cfg` files, settings/log/manifest files, absolute paths
     from the build machine (also inside `version_info.txt` and docs).
  3. Confirm `.gitignore` matches SPEC 12 and `git status --ignored` shows
     runtime files ignored.
  4. Fill in the real repo URL (Q3) if known.
  5. Produce the pre-publish checklist below, ticked.
- **Pre-publish checklist (to be ticked in step 21):**
  - [ ] `git config user.name` / `user.email` are what you want public
        (consider GitHub's `<id>+<username>@users.noreply.github.com`).
  - [ ] `git log --format="%an <%ae>"` shows no unwanted names/emails in
        any commit.
  - [ ] History reviewed (`git log -p`) — no personal data was ever committed
        and later removed (if it was, rewrite history before publishing).
  - [ ] No secrets, tokens, or keys (`git grep -i -E "token|secret|password|api[_-]?key"`).
  - [ ] No `.cfg`, `settings.json`, `log*.txt`, `manifest.json`, `build/`,
        `dist/`, `.venv/` tracked (`git ls-files`).
  - [ ] Release .exe built from a clean checkout; attach it to a GitHub
        Release, not to the repo.
  - [ ] README disclaimer and LICENSE present.
- **Acceptance:** list of checked files and patterns, scan output clean (or
  each finding justified), checklist ticked.
