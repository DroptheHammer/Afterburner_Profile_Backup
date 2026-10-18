"""Windows-only helpers: find/close Afterburner, registry, admin rights, UNC paths.

Everything here imports safely on non-Windows and returns safe defaults.
"""
import os
import re
import subprocess
import sys
import time

AFTERBURNER_EXE: str = "MSIAfterburner.exe"
_NO_WINDOW = 0x08000000


def is_windows() -> bool:
    return sys.platform == "win32"


def run_hidden(args: list[str], timeout_s: float = 15.0) -> tuple[int, str]:
    """Run a command with no console window; return (returncode, stdout+stderr)."""
    try:
        flags = _NO_WINDOW if is_windows() else 0
        p = subprocess.run(args, capture_output=True, text=True, errors="replace",
                           timeout=timeout_s, creationflags=flags)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:  # noqa: BLE001 - public functions never raise
        return -1, str(exc)


def find_afterburner_process_paths() -> list[str]:
    """Full paths of running MSIAfterburner.exe processes. [] on error or non-Windows."""
    if not is_windows():
        return []
    try:
        import ctypes
        from ctypes import wintypes as wt
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        pdw = ctypes.POINTER(wt.DWORD)
        psapi.EnumProcesses.argtypes = [pdw, wt.DWORD, pdw]
        psapi.EnumProcesses.restype = wt.BOOL
        k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k32.OpenProcess.restype = wt.HANDLE
        k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR,
                                                   ctypes.POINTER(wt.DWORD)]
        k32.QueryFullProcessImageNameW.restype = wt.BOOL
        k32.CloseHandle.argtypes = [wt.HANDLE]
        k32.CloseHandle.restype = wt.BOOL
        count = 1024
        while True:
            pids = (wt.DWORD * count)()
            needed = wt.DWORD(0)
            if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(needed)):
                return []
            if needed.value < ctypes.sizeof(pids):
                break
            count *= 2
        found: list[str] = []
        for pid in pids[: needed.value // ctypes.sizeof(wt.DWORD)]:
            handle = k32.OpenProcess(0x1000, False, pid) if pid else None
            if not handle:
                continue
            try:
                buf = ctypes.create_unicode_buffer(32768)
                size = wt.DWORD(len(buf))
                if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                    if os.path.basename(buf.value).lower() == AFTERBURNER_EXE.lower():
                        found.append(buf.value)
            finally:
                k32.CloseHandle(handle)
        return found
    except Exception:  # noqa: BLE001
        return []


def is_afterburner_running() -> bool:
    """True if MSIAfterburner.exe is running (process list, then tasklist as backup)."""
    if not is_windows():
        return False
    try:
        if find_afterburner_process_paths():
            return True
        _code, out = run_hidden(["tasklist", "/FI", "IMAGENAME eq " + AFTERBURNER_EXE, "/NH"])
        return AFTERBURNER_EXE.lower() in out.lower()
    except Exception:  # noqa: BLE001
        return False


def _folder_from_command(text: str) -> str:
    """Folder of the program named in a DisplayIcon/UninstallString value."""
    text = text.strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        text = text[1:end] if end > 0 else text[1:]
    else:
        m = re.match(r"(.*?\.(?:exe|ico))\b", text, re.IGNORECASE)
        text = m.group(1) if m else re.sub(r",\s*-?\d+$", "", text)
    text = re.sub(r",\s*-?\d+$", "", text.strip().strip('"'))
    return os.path.dirname(text) if text else ""


def registry_install_dirs() -> list[str]:
    """Existing MSI Afterburner folders found in the Uninstall registry keys."""
    if not is_windows():
        return []
    try:
        import winreg
        sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        sub32 = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        places = [(winreg.HKEY_LOCAL_MACHINE, sub), (winreg.HKEY_LOCAL_MACHINE, sub32),
                  (winreg.HKEY_CURRENT_USER, sub)]
        result: list[str] = []
        for hive, path in places:
            try:
                root = winreg.OpenKey(hive, path)
            except OSError:
                continue
            with root:
                for i in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        with winreg.OpenKey(root, winreg.EnumKey(root, i)) as key:
                            def val(name: str) -> str:
                                try:
                                    return str(winreg.QueryValueEx(key, name)[0] or "")
                                except OSError:
                                    return ""
                            if "msi afterburner" not in val("DisplayName").lower():
                                continue
                            folder = val("InstallLocation").strip().strip('"')
                            for name in ("DisplayIcon", "UninstallString"):
                                if not folder and val(name):
                                    folder = _folder_from_command(val(name))
                            folder = os.path.normpath(folder) if folder else ""
                            if folder and os.path.isdir(folder) and folder not in result:
                                result.append(folder)
                    except OSError:
                        continue
        return result
    except Exception:  # noqa: BLE001
        return []


def default_install_dirs() -> list[str]:
    """Usual install folders, built from the Program Files environment variables."""
    x86 = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
    pf = os.environ.get("ProgramFiles") or r"C:\Program Files"
    return [os.path.join(x86, "MSI Afterburner"), os.path.join(pf, "MSI Afterburner")]


def find_install_dir() -> tuple[str | None, str]:
    """Return (folder, how_found); the first candidate with a Profiles folder wins."""
    try:
        test = os.environ.get("ABPB_TEST_INSTALL_DIR")
        if test and os.path.isdir(os.path.join(test, "Profiles")):
            return test, "test"
        running = [os.path.dirname(p) for p in find_afterburner_process_paths()]
        for how, cands in (("running", running), ("registry", registry_install_dirs()),
                           ("default", default_install_dirs())):
            for folder in cands:
                if os.path.isdir(os.path.join(folder, "Profiles")):
                    return folder, how
    except Exception:  # noqa: BLE001
        pass
    return None, "none"


def close_afterburner(force: bool = False, timeout_s: float = 8.0) -> tuple[bool, str]:
    """Ask Windows to close Afterburner (taskkill), then wait until it is gone."""
    try:
        if not is_afterburner_running():
            return True, "Afterburner is closed."
        args = ["taskkill", "/IM", AFTERBURNER_EXE] + (["/F"] if force else [])
        _code, out = run_hidden(args)
        if "access is denied" in out.lower():
            return False, ("Windows needs administrator permission to close Afterburner. "
                           "Please close it yourself, or restart this app as administrator.")
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if not is_afterburner_running():
                return True, "Afterburner is closed."
            time.sleep(0.5)
        if not is_afterburner_running():
            return True, "Afterburner is closed."
        return False, "Afterburner did not close in time."
    except Exception as exc:  # noqa: BLE001
        return False, f"We couldn't close Afterburner: {exc}"


def is_admin() -> bool:
    """True if this program runs with administrator rights."""
    if not is_windows():
        return False
    try:
        import ctypes
        shell32 = ctypes.WinDLL("shell32")
        shell32.IsUserAnAdmin.argtypes = []
        shell32.IsUserAnAdmin.restype = ctypes.c_int
        return bool(shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def relaunch_as_admin(extra_args: list[str]) -> bool:
    """Start this app again with a UAC prompt. True if Windows launched it."""
    if not is_windows():
        return False
    try:
        import ctypes
        from ctypes import wintypes as wt
        args = list(extra_args)
        if not getattr(sys, "frozen", False):
            args.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"))
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.ShellExecuteW.argtypes = [wt.HWND, wt.LPCWSTR, wt.LPCWSTR, wt.LPCWSTR,
                                          wt.LPCWSTR, ctypes.c_int]
        shell32.ShellExecuteW.restype = wt.HINSTANCE
        ret = shell32.ShellExecuteW(None, "runas", sys.executable,
                                    subprocess.list2cmdline(args), None, 1)
        return (ret or 0) > 32
    except Exception:  # noqa: BLE001
        return False


def to_unc_path(path: str) -> str:
    """Turn a mapped-drive path (Z:\\x) into \\\\server\\share\\x. Otherwise unchanged."""
    try:
        if not is_windows() or not re.match(r"^[A-Za-z]:", path or ""):
            return path
        import ctypes
        from ctypes import wintypes as wt
        mpr = ctypes.WinDLL("mpr", use_last_error=True)
        mpr.WNetGetConnectionW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
        mpr.WNetGetConnectionW.restype = wt.DWORD
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(len(buf))
        if mpr.WNetGetConnectionW(path[:2], buf, ctypes.byref(size)) != 0 or not buf.value:
            return path
        return buf.value.rstrip("\\") + path[2:]
    except Exception:  # noqa: BLE001
        return path
