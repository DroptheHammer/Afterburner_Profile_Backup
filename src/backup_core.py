"""All file logic for Afterburner Profile Backup (no UI, no Windows API calls)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime

import version

MAIN_CFG_NAME: str = "MSIAfterburner.cfg"
PROFILES_DIR_NAME: str = "Profiles"
MANIFEST_NAME: str = "manifest.json"
BEFORE_RESTORE_DIR_NAME: str = "before-restore"
TEMP_SUFFIX: str = ".abpb-tmp"
FOLDER_TIME_FORMAT: str = "%Y-%m-%d_%H-%M-%S"

_FOLDER_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})(?:_\d+)?$")
_WRITE_TEST_NAME = ".abpb-write-test"


@dataclass(frozen=True)
class ProfileFile:
    rel_path: str        # see SPEC 5.1
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
    created: datetime            # manifest created_local; else folder name; else mtime
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
def sha256_file(path: str) -> str:
    """Lowercase hex SHA-256, reading in 1 MiB chunks. Raises OSError."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def friendly_size(num_bytes: int) -> str:
    """Human-friendly size: "512 bytes", "1.2 KB", "3.4 MB"."""
    if num_bytes < 1024:
        return f"{num_bytes} bytes"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def friendly_datetime(dt: datetime) -> str:
    """e.g. "Sun 18 Oct 2026, 2:03 PM" (hour without a leading zero, works on Windows)."""
    text = dt.strftime("%a %d %b %Y, %I:%M %p")
    head, sep, tail = text.partition(", ")
    return head + sep + tail.lstrip("0")


def count_text(n: int) -> str:
    """"1 profile" or "<n> profiles"."""
    return "1 profile" if n == 1 else f"{n} profiles"


def make_backup_folder_name(now: datetime) -> str:
    """Folder name for a backup made at `now` (local time)."""
    return now.strftime(FOLDER_TIME_FORMAT)


def parse_backup_folder_name(name: str) -> datetime | None:
    """Inverse of make_backup_folder_name; accepts an optional "_<digits>" suffix."""
    match = _FOLDER_NAME_RE.match(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), FOLDER_TIME_FORMAT)
    except ValueError:
        return None


def is_safe_rel_path(rel_path: str) -> bool:
    """True only for "MSIAfterburner.cfg" or "Profiles/<name>.cfg" (see SPEC 5.1)."""
    if rel_path == MAIN_CFG_NAME:
        return True
    prefix = PROFILES_DIR_NAME + "/"
    if not rel_path.startswith(prefix):
        return False
    name = rel_path[len(prefix):]
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        return False
    return name.lower().endswith(".cfg")


def is_valid_install_dir(path: str | None) -> bool:
    """True if path is a folder containing a Profiles subfolder."""
    if not path:
        return False
    return os.path.isdir(os.path.join(path, PROFILES_DIR_NAME))


def _profile_file(rel_path: str, abs_path: str) -> ProfileFile | None:
    try:
        st = os.stat(abs_path)
    except OSError:
        return None
    return ProfileFile(rel_path, abs_path, st.st_size, st.st_mtime)


def list_profile_files(install_dir: str, include_main_cfg: bool = True) -> list[ProfileFile]:
    """All *.cfg files in <install>/Profiles (sorted), then the main cfg if wanted."""
    profiles_dir = os.path.join(install_dir, PROFILES_DIR_NAME)
    try:
        names = os.listdir(profiles_dir)
    except OSError:
        return []
    result: list[ProfileFile] = []
    for name in sorted(names, key=str.lower):
        full = os.path.join(profiles_dir, name)
        if name.lower().endswith(".cfg") and os.path.isfile(full):
            item = _profile_file(f"{PROFILES_DIR_NAME}/{name}", full)
            if item is not None:
                result.append(item)
    if include_main_cfg:
        main = os.path.join(install_dir, MAIN_CFG_NAME)
        if os.path.isfile(main):
            item = _profile_file(MAIN_CFG_NAME, main)
            if item is not None:
                result.append(item)
    return result


def check_folder_writable(folder: str) -> tuple[bool, str]:
    """Check the folder exists and we can save a file in it. Returns (ok, message)."""
    if not os.path.exists(folder):
        return (False, "We can't reach this folder. If it is on a network drive or NAS, "
                       "make sure it is turned on and connected, then try again.")
    if not os.path.isdir(folder):
        return (False, "This is a file, not a folder. Please pick a folder.")
    test_path = os.path.join(folder, _WRITE_TEST_NAME)
    try:
        with open(test_path, "wb") as f:
            f.write(b"test")
        os.remove(test_path)
    except OSError:
        return (False, "We can't save files in this folder. Pick a different folder or "
                       "check that you have permission to save there.")
    return (True, "")


# ---- backup (step 4) ----
def write_manifest(folder: str, kind: str, source_dir: str, records: list[FileRecord],
                   now: datetime) -> None:
    """Write manifest.json (SPEC 5.3) into folder. Raises OSError."""
    data = {
        "app": version.APP_NAME,
        "app_version": version.VERSION,
        "manifest_version": 1,
        "kind": kind,
        "created_local": now.replace(microsecond=0).isoformat(),
        "source_dir": source_dir,
        "files": [{"rel_path": r.rel_path, "size": r.size, "sha256": r.sha256}
                  for r in records],
    }
    with open(os.path.join(folder, MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_manifest(folder: str) -> dict | None:
    """Parsed manifest, or None if missing/broken. Drops entries with unsafe rel_paths."""
    try:
        with open(os.path.join(folder, MANIFEST_NAME), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return None
    data["files"] = [e for e in data["files"] if isinstance(e, dict)
                     and isinstance(e.get("rel_path"), str) and is_safe_rel_path(e["rel_path"])]
    return data


def unique_backup_folder(parent: str, now: datetime) -> str:
    """Path <parent>/<name> that does not exist yet (adds _2, _3 ...). Not created."""
    base = os.path.join(parent, make_backup_folder_name(now))
    path, n = base, 2
    while os.path.exists(path):
        path = f"{base}_{n}"
        n += 1
    return path


def copy_verified(src: str, dst: str) -> tuple[int, str]:
    """Copy src to dst via a temp file, verify by hash, then move into place."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + TEMP_SUFFIX
    shutil.copy2(src, tmp)
    src_hash = sha256_file(src)
    if sha256_file(tmp) != src_hash:
        raise ValueError("verify failed")
    os.replace(tmp, dst)
    return (os.path.getsize(dst), src_hash)


def create_backup(install_dir: str, backup_root: str, include_main_cfg: bool = True,
                  dry_run: bool = False, kind: str = "backup",
                  now: datetime | None = None) -> OpResult:
    """Back up the profiles into a new dated folder (SPEC 6.4)."""
    files = list_profile_files(install_dir, include_main_cfg)
    if not files:
        return OpResult(False, f"We didn't find any profiles to back up in {install_dir}.",
                        dry_run=dry_run)
    parent = backup_root
    if kind == "before-restore":
        parent = os.path.join(backup_root, BEFORE_RESTORE_DIR_NAME)
        if not dry_run and os.path.isdir(backup_root):
            try:
                os.makedirs(parent, exist_ok=True)
            except OSError:
                pass  # the writable check below reports the problem
    ok, msg = check_folder_writable(backup_root)
    if not ok:
        return OpResult(False, msg, dry_run=dry_run)
    now = now or datetime.now()
    folder = unique_backup_folder(parent, now)
    count = len(files)
    if dry_run:
        details = [f"Would copy {f.rel_path} ({friendly_size(f.size)})" for f in files]
        return OpResult(True, f"Test run: would back up {count_text(count)} to {folder}. "
                              "Nothing was changed.", details, folder, count, True)
    details: list[str] = []
    records: list[FileRecord] = []
    try:
        for f in files:
            size, digest = copy_verified(f.abs_path, os.path.join(folder, *f.rel_path.split("/")))
            records.append(FileRecord(f.rel_path, size, digest))
            details.append(f"Copied {f.rel_path} ({friendly_size(size)})")
        write_manifest(folder, kind, install_dir, records, now)
    except (OSError, ValueError) as exc:
        reason = ("a copied file did not match the original"
                  if isinstance(exc, ValueError) else (exc.strerror or str(exc)))
        return OpResult(False, f"The backup did not finish: {reason}. "
                               "Your original profiles were not changed.",
                        details, folder, len(records), False)
    return OpResult(True, f"Backed up {count_text(count)} to {folder}. Verified OK.",
                    details, folder, count, False)


# ---- list (step 5) ----
def _records_from_manifest(manifest: dict | None) -> list[FileRecord]:
    records: list[FileRecord] = []
    for e in (manifest or {}).get("files", []):
        size, digest = e.get("size"), e.get("sha256")
        if isinstance(size, int) and isinstance(digest, str):
            records.append(FileRecord(e["rel_path"], size, digest.lower()))
    return records


def _backup_info(folder: str, default_kind: str) -> BackupInfo | None:
    """BackupInfo for one folder, or None if it is neither dated nor has a manifest."""
    parsed = parse_backup_folder_name(os.path.basename(folder))
    manifest = read_manifest(folder)
    if parsed is None and not os.path.isfile(os.path.join(folder, MANIFEST_NAME)):
        return None
    data = manifest or {}
    kind = data.get("kind") if data.get("kind") in ("backup", "before-restore") else default_kind
    created = None
    try:
        created = datetime.fromisoformat(str(data["created_local"])).replace(tzinfo=None)
    except (KeyError, ValueError):
        created = parsed
    if created is None:
        try:
            created = datetime.fromtimestamp(os.path.getmtime(folder))
        except (OSError, ValueError, OverflowError):
            created = datetime.min
    source = data.get("source_dir")
    return BackupInfo(folder, kind, created, source if isinstance(source, str) else "",
                      _records_from_manifest(manifest), manifest is not None)


def list_backups(backup_root: str) -> list[BackupInfo]:
    """All backups (and automatic safety copies) under backup_root, newest first."""
    found: list[BackupInfo] = []
    for parent, kind in ((backup_root, "backup"),
                         (os.path.join(backup_root, BEFORE_RESTORE_DIR_NAME), "before-restore")):
        try:
            names = os.listdir(parent)
        except OSError:
            continue
        for name in names:
            full = os.path.join(parent, name)
            if (parent == backup_root and name == BEFORE_RESTORE_DIR_NAME) \
                    or not os.path.isdir(full):
                continue
            info = _backup_info(full, kind)
            if info is not None:
                found.append(info)
    found.sort(key=lambda i: (i.created, i.folder), reverse=True)
    return found


def verify_backup(info: BackupInfo, rel_paths: list[str] | None = None) -> tuple[bool, list[str]]:
    """Check the selected files exist in the backup and match size and sha256."""
    if not info.manifest_ok:
        return (False, ["This backup's details are missing, so it can't be checked."])
    wanted = None if rel_paths is None else set(rel_paths)
    problems: list[str] = []
    for rec in info.files:
        if wanted is not None and rec.rel_path not in wanted:
            continue
        name = rec.rel_path.split("/")[-1]
        path = os.path.join(info.folder, *rec.rel_path.split("/"))
        if not os.path.isfile(path):
            problems.append(f"{name} is missing from the backup.")
            continue
        try:
            good = os.path.getsize(path) == rec.size and sha256_file(path) == rec.sha256
        except OSError:
            good = False
        if not good:
            problems.append(f"{name} in the backup is damaged (it doesn't match the original).")
    return (not problems, problems)


def backup_label(info: BackupInfo) -> str:
    """One line for the backup list, e.g. "Sun 18 Oct 2026, 2:03 PM — 7 profiles"."""
    text = f"{friendly_datetime(info.created)} — {count_text(len(info.files))}"
    if info.kind == "before-restore":
        text += " (automatic safety copy made before a restore)"
    if not info.manifest_ok:
        text += " (details missing — can't be checked)"
    return text


# ---- restore (step 6) ----
def target_path_for(install_dir: str, rel_path: str) -> str:
    """Absolute destination of rel_path inside install_dir. Raises ValueError if unsafe."""
    if not is_safe_rel_path(rel_path):
        raise ValueError(f"unsafe path: {rel_path}")
    return os.path.join(install_dir, *rel_path.split("/"))


def restore_files(info: BackupInfo, rel_paths: list[str], install_dir: str,
                  backup_root: str, include_main_cfg: bool = True, dry_run: bool = False,
                  now: datetime | None = None) -> OpResult:
    """Put selected profiles from a backup back into install_dir (SPEC 6.4)."""
    if not rel_paths:
        return OpResult(False, "Please pick at least one profile to restore.", dry_run=dry_run)
    wanted = list(dict.fromkeys(rel_paths))
    known = {r.rel_path for r in info.files}
    if any(not is_safe_rel_path(p) or p not in known for p in wanted):
        return OpResult(False, "One of the chosen profiles is not part of this backup, "
                               "so nothing was restored.", dry_run=dry_run)
    good, problems = verify_backup(info, wanted)
    if not good:
        return OpResult(False, f"This backup can't be used safely: {problems[0]}", problems,
                        info.folder, dry_run=dry_run)
    if not dry_run and not check_folder_writable(install_dir)[0]:
        return OpResult(False, "We can't write to the Afterburner folder. Restoring needs "
                               "administrator permission.", dry_run=dry_run)
    safety_main = include_main_cfg or MAIN_CFG_NAME in wanted  # never overwrite it unsaved
    had_current = bool(list_profile_files(install_dir, safety_main))
    safety = create_backup(install_dir, backup_root, safety_main, dry_run,
                           kind="before-restore", now=now)
    if not safety.ok and had_current:
        return OpResult(False, "We couldn't make a safety copy of your current profiles, so "
                               f"nothing was restored: {safety.message}", dry_run=dry_run)
    safety_folder = safety.folder if safety.ok and not dry_run else None
    count = len(wanted)
    if dry_run:
        details = [("Would replace " if os.path.isfile(target_path_for(install_dir, p))
                    else "Would add ") + p for p in wanted]
        return OpResult(True, f"Test run: would restore {count_text(count)}. "
                              "Nothing was changed.", details, info.folder, count, True)
    details: list[str] = []
    try:
        for p in wanted:
            target = target_path_for(install_dir, p)
            existed = os.path.isfile(target)
            copy_verified(os.path.join(info.folder, *p.split("/")), target)
            details.append(("Replaced " if existed else "Added ") + p)
    except (OSError, ValueError) as exc:
        reason = ("a copied file did not match the original"
                  if isinstance(exc, ValueError) else (exc.strerror or str(exc)))
        done = len(details)
        details += [f"Not restored: {p}" for p in wanted[done:]]
        where = (f"A safety copy of your previous profiles is in {safety_folder}."
                 if safety_folder else "There were no previous profiles to make a safety copy of.")
        return OpResult(False, f"The restore did not finish: {reason}. {where}", details,
                        info.folder, done, False, safety_folder)
    return OpResult(True, f"Restored {count_text(count)}. Verified OK. "
                          "Please open Afterburner again.", details, info.folder, count,
                    False, safety_folder)
