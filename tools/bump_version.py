"""Set the app version everywhere it appears: py tools\\bump_version.py 1.0.1"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION_RE = re.compile(r'^VERSION: str = "(\d+\.\d+\.\d+)"', re.MULTILINE)


def current_version(root: str = REPO) -> str:
    with open(os.path.join(root, "src", "version.py"), encoding="utf-8") as f:
        match = _VERSION_RE.search(f.read())
    if not match:
        raise ValueError("VERSION not found in src/version.py")
    return match.group(1)


def _parse(version: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version must look like 1.2.3, got %r" % version)
    major, minor, patch = (int(p) for p in version.split("."))
    return major, minor, patch


def _rewrite(path: str, replacements: list[tuple[str, str]]) -> None:
    with open(path, encoding="utf-8", newline="") as f:  # keep the file's line endings
        text = f.read()
    for pattern, new in replacements:
        text, count = re.subn(pattern, new, text, flags=re.MULTILINE)
        if count == 0:
            raise ValueError("Pattern %r not found in %s" % (pattern, path))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def bump(new: str, root: str = REPO) -> str:
    """Write `new` into src/version.py and version_info.txt. Returns the old version."""
    old = current_version(root)
    if _parse(new) <= _parse(old):
        raise ValueError("New version %s must be higher than the current %s" % (new, old))
    major, minor, patch = _parse(new)
    _rewrite(os.path.join(root, "src", "version.py"),
             [(r'^VERSION: str = "[\d.]+"', 'VERSION: str = "%s"' % new)])
    four = "%d, %d, %d, 0" % (major, minor, patch)
    _rewrite(os.path.join(root, "version_info.txt"), [
        (r"filevers=\([\d, ]+\)", "filevers=(%s)" % four),
        (r"prodvers=\([\d, ]+\)", "prodvers=(%s)" % four),
        (r"'FileVersion', '[\d.]+'", "'FileVersion', '%s.0'" % new),
        (r"'ProductVersion', '[\d.]+'", "'ProductVersion', '%s.0'" % new),
    ])
    return old


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: py tools\\bump_version.py <new version, e.g. 1.0.1>")
        print("Current version: %s" % current_version())
        return 2
    try:
        old = bump(argv[0])
    except ValueError as exc:
        print("Not changed: %s" % exc)
        return 1
    print("Version changed from %s to %s (src/version.py, version_info.txt)." % (old, argv[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
