# Developer Guide

For people who want to build, test, or change the app. Users do not need this.

## Requirements

- Windows 10 or 11.
- Python 3.10 or newer. It is needed to **build** the app only. People who
  run the finished `.exe` need nothing installed.
- PyInstaller, listed in `requirements-dev.txt` (developer only).

**Stdlib-only rule:** the app code uses only the Python standard library
(`tkinter`, `ctypes`, `winreg`, `unittest`, ...). Do not add third-party
packages to `src/`. PyInstaller is a build tool, not a runtime dependency.

## Build

```
build.bat
```

It does these steps and stops with a plain message if one fails:

1. Finds Python (`py -3`, else `python`).
2. Creates `.venv` if missing and installs `requirements-dev.txt`.
3. Runs the unit tests.
4. Runs PyInstaller (`--onefile --windowed`, `docs\QUICKSTART.md` bundled, and one
   `--hidden-import` per screen module; add one whenever you add a screen).
5. Prints the path of the result.

Output: `dist\AfterburnerProfileBackup.exe`

Use `build.bat nopause` to skip the final "press a key" pause (for scripts).

The `.exe` runs normally and asks for administrator permission only when
restoring. To always require admin instead, add `--uac-admin` to the
PyInstaller line in `build.bat`.

## Layout

```
src/
  main.py            entry point, arguments, DPI, crash handler
  version.py         name, version, license, disclaimer
  settings.py        settings file, log file, resource paths
  backup_core.py     ALL file logic
  winutils.py        Windows-only: processes, registry, admin, UNC
  ui.py              App window, screen switching, home screen
  ui_widgets.py      shared widgets, fonts, status bar, background tasks
  ui_firstrun.py     "Is this correct?" screen
  ui_backup.py       backup screen
  ui_restore.py      restore step 1
  ui_restore_select.py  restore step 2
  ui_settings.py     settings screen
  ui_help.py         help viewer and About box
tests/               unittest files and helpers.py
tools/               make_fake_install.py, privacy_scan.py
docs/                QUICKSTART, FAQ, TROUBLESHOOTING, DEVELOPER
```

Modules import each other by plain name (`import backup_core`). `src/` is on
`sys.path` (PyInstaller `--paths src`; tests add it).

## Module boundaries

- `backup_core.py` must not import `tkinter`, `winreg`, `ctypes`, or any `ui*`.
- `ui*.py` must not open, copy, or hash files. They call `backup_core`,
  `winutils`, and `settings`. (`ui_help.py` reads help text through
  `settings.read_help_text()`.)
- `winutils.py` must import on non-Windows too. Guard `winreg` and
  `ctypes.windll` inside functions and return safe defaults.
- Every module starts with a short docstring. Public functions have type
  hints. Maximum line length is 100.

`SPEC.md` is the source of truth for names, wording, and behavior.

## Run the tests

```
py -m unittest discover -s tests -v
```

Tests never touch real Afterburner files or real settings. They set
`ABPB_SETTINGS_DIR` to a temp folder.

## Run from source

```
py src\main.py
```

Options:

- `--restore` opens straight on the restore screen.
- `--selftest-ui` builds every screen, prints one line per screen
  (`OK home`, `FAIL backup: ...`), and exits with code 0 if all are OK.

```
py src\main.py --selftest-ui
echo %errorlevel%
```

The same flags work on the built `.exe`.

## Environment variables for testing

- `ABPB_TEST_INSTALL_DIR`: if set to a folder that has a `Profiles`
  subfolder, the app uses it as the Afterburner folder.
- `ABPB_SETTINGS_DIR`: use this folder for `settings.json` and `log.txt`
  instead of `%LOCALAPPDATA%\AfterburnerProfileBackup`.

## Try it with a fake Afterburner

```
py tools\make_fake_install.py C:\Users\<you>\fake
```

It creates a fake install and prints a line like
`set ABPB_TEST_INSTALL_DIR=<path>`. Run that line in the same window, then
start the app with `py src\main.py`. Use `ABPB_SETTINGS_DIR` too, so your
real settings are not changed.

## Privacy scan

```
py tools\privacy_scan.py
```

It scans the repo for emails, IP addresses, user folders, network paths,
your user and computer names, and any `.cfg` file. It prints
`file:line:reason` and exits with code 1 if it finds anything. Run it before
every commit. See SPEC.md section 12 for the rules. Use placeholder paths
only, such as `C:\Users\<you>\...`, `\\NAS\share\AfterburnerBackups`, and
`D:\Backups\Afterburner`.

## Releasing

See [RELEASING.md](RELEASING.md). In short: update `CHANGELOG.md`, run
`py tools\bump_version.py X.Y.Z`, `build.bat`, `py tools\make_release_notes.py X.Y.Z`,
then commit, tag `vX.Y.Z`, push, and `gh release create`.

## License

MIT. Downloads are published on the project's GitHub Releases page
(`https://github.com/DroptheHammer/Afterburner_Profile_Backup`).
