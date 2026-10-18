# Releasing a new version

How to publish a new version on GitHub. Run everything from the repo root.

Version numbers look like `MAJOR.MINOR.PATCH`:
- PATCH (1.0.0 → 1.0.1): bug fixes only.
- MINOR (1.0.1 → 1.1.0): new features that don't change how existing ones work.
- MAJOR (1.1.0 → 2.0.0): big changes, or backups that older versions can't read.

## One-time setup

1. Install the GitHub CLI: `winget install --id GitHub.cli`
2. Sign in once: `gh auth login` (choose GitHub.com, HTTPS, and log in with a web browser).

## Steps

1. **Changelog.** In `CHANGELOG.md`, make sure the new version has a section, written in
   plain words for gamers. Change its heading to `## X.Y.Z (YYYY-MM-DD)`.
2. **Version number.** `py tools\bump_version.py X.Y.Z`
   (updates `src/version.py` and `version_info.txt`).
3. **Build and test.** `build.bat nopause` (runs all tests, then builds the .exe). Then:
   `dist\AfterburnerProfileBackup.exe --selftest-ui` must exit with code 0
   (in cmd: `start /wait dist\AfterburnerProfileBackup.exe --selftest-ui` then `echo %errorlevel%`).
4. **Privacy.** `py tools\privacy_scan.py` must report 0 findings.
5. **Release notes.** `py tools\make_release_notes.py X.Y.Z`
   (writes `dist\RELEASE_NOTES_vX.Y.Z.md` with the changelog section and the .exe's SHA-256).
6. **Commit and tag.**
   ```
   git add -A
   git commit -m "Release X.Y.Z"
   git tag -a vX.Y.Z -m "Afterburner Profile Backup X.Y.Z"
   git push --follow-tags
   ```
7. **Publish.**
   ```
   gh release create vX.Y.Z dist\AfterburnerProfileBackup.exe --title "Afterburner Profile Backup X.Y.Z" --notes-file dist\RELEASE_NOTES_vX.Y.Z.md
   ```
8. **Check.** Open the release page, download the .exe, compare its SHA-256 with the notes
   (`certutil -hashfile AfterburnerProfileBackup.exe SHA256`), and double-click it once.

## Rules

- Upload exactly the .exe that `make_release_notes.py` hashed. If you rebuild, rerun step 5.
- The .exe goes on the Release page only. Never commit `dist/` or `build/`.
- Start a new `## X.Y.Z (not released yet)` section in `CHANGELOG.md` for the next version
  as soon as you change something.
