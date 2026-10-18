"""Scan the repository for personal data (SPEC section 12). Standard library only.

Usage: py tools/privacy_scan.py [folder]   (default: the repo root)
Prints path:line:reason for each finding. Exit code 1 if anything was found, else 0.
"""
import os
import re
import sys

SKIP_DIRS = {".git", ".venv", "build", "dist", "__pycache__", ".claude"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
IPV4 = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w]|\.\d)")
# Drive-letter user folders; backslashes may be doubled (Python/JSON source text).
USER_DIR = re.compile(r"[A-Za-z]:\\{1,4}Users\\{1,4}([^\\/\s\"'<>|*?%]+)", re.IGNORECASE)
# Server and share parts of a UNC path (two to four leading backslashes).
UNC = re.compile(r"(?<![\w:.>\\])\\{2,4}([\w.$-]+)\\{1,4}([\w.$-]+)")
ALLOWED_UNC = {("nas", "share"), ("server", "share")}
ALLOWED_IPS = {"0.0.0.0", "127.0.0.1"}


def check_line(line: str, base: str, env_names: list[str]) -> list[str]:
    """Return the reasons (possibly none) why one line of text is a privacy problem."""
    found = [f"email address: {m.group(0)}" for m in EMAIL.finditer(line)]
    if base.lower() != "version_info.txt":
        for m in IPV4.finditer(line):
            ip = m.group(1)
            if ip not in ALLOWED_IPS and all(int(p) <= 255 for p in ip.split(".")):
                found.append(f"IPv4 address: {ip}")
    found += [f"user folder: {m.group(0)}" for m in USER_DIR.finditer(line)]
    for m in UNC.finditer(line):
        if (m.group(1).lower(), m.group(2).lower()) not in ALLOWED_UNC:
            found.append(f"network path: {m.group(0)}")
    low = line.lower()
    for name in env_names:
        if re.search(r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])", low):
            found.append("contains the current user or computer name (not shown)")
    return found


def scan(root: str) -> list[tuple[str, int, str]]:
    """Walk root and return (path, line, reason) for every finding. Line 0 = whole file."""
    env_names = [v for v in (os.environ.get("USERNAME"), os.environ.get("COMPUTERNAME"))
                 if v and v.strip()]
    results: list[tuple[str, int, str]] = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = os.path.join(folder, name)
            if name.lower().endswith(".cfg"):
                results.append((path, 0, "a .cfg file must not be in the repository"))
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if b"\0" in data[:4096]:
                continue  # binary file
            text = data.decode("utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                for reason in check_line(line, name, env_names):
                    results.append((path, number, reason))
    return results


def main(argv: list[str]) -> int:
    """Command line entry point. Returns 1 if anything was found, else 0."""
    root = argv[1] if len(argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    findings = scan(root)
    for path, line, reason in findings:
        print(f"{os.path.relpath(path, root)}:{line}:{reason}")
    print(f"Privacy scan: {len(findings)} finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
