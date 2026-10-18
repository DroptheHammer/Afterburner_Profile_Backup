"""Write dist/RELEASE_NOTES_v<version>.md from CHANGELOG.md and the built .exe.

Usage: py tools\\make_release_notes.py 1.0.1
"""
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
import version  # noqa: E402

EXE = os.path.join(REPO, "dist", "AfterburnerProfileBackup.exe")

FOOTER = """### How to use it
1. Download **AfterburnerProfileBackup.exe** below.
2. Double-click it. No install needed.
3. Follow the screens. The Help button has a step-by-step guide.

### "Windows protected your PC"?
This free app is not code-signed, so Windows SmartScreen may warn you the first time. \
Click **More info**, then **Run anyway**. Only download the app from this Releases page.

### Check your download (optional)
SHA-256 of `AfterburnerProfileBackup.exe`:
```
{sha}
```

{disclaimer}
"""


def changelog_section(ver: str, root: str = REPO) -> str:
    """Text under '## <ver>' in CHANGELOG.md, up to the next '## ' heading."""
    with open(os.path.join(root, "CHANGELOG.md"), encoding="utf-8") as f:
        text = f.read()
    match = re.search(r"^## %s\b[^\n]*\n(.*?)(?=^## |\Z)" % re.escape(ver), text,
                      re.MULTILINE | re.DOTALL)
    if not match or not match.group(1).strip():
        raise ValueError("CHANGELOG.md has no entry for %s" % ver)
    return match.group(1).strip()


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main(argv: list[str]) -> int:
    ver = argv[0] if argv else version.VERSION
    if ver != version.VERSION:
        print("Not written: src/version.py says %s, not %s. Run bump_version.py first."
              % (version.VERSION, ver))
        return 1
    try:
        changes = changelog_section(ver)
        sha = sha256(EXE)
    except (OSError, ValueError) as exc:
        print("Not written: %s" % exc)
        return 1
    body = "## %s %s\n\n%s\n\n%s" % (version.APP_NAME, ver, changes,
                                     FOOTER.format(sha=sha, disclaimer=version.DISCLAIMER))
    out = os.path.join(REPO, "dist", "RELEASE_NOTES_v%s.md" % ver)
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    print("Wrote %s (SHA-256 %s)" % (out, sha))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
