"""Test helpers: put src/ on sys.path and build a fake Afterburner install."""
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GPU_PROFILE = "VEN_10DE&DEV_0000&SUBSYS_00000000&REV_A1&BUS_1&DEV_0&FN_0.cfg"


def add_src_to_path() -> None:
    """Insert <repo>/src at sys.path[0] once."""
    src = os.path.join(_REPO, "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def make_fake_install(root: str, profile_names: list[str] | None = None,
                      with_main_cfg: bool = True) -> str:
    """Create <root>/MSI Afterburner/Profiles with fake .cfg files; return the install folder."""
    names = profile_names or ["Profile1.cfg", "Profile2.cfg", _GPU_PROFILE]
    install = os.path.join(root, "MSI Afterburner")
    profiles = os.path.join(install, "Profiles")
    os.makedirs(profiles, exist_ok=True)
    for name in names:
        with open(os.path.join(profiles, name), "w", encoding="utf-8", newline="") as f:
            f.write("[Startup]\nFormat=2\n" + name)
    if with_main_cfg:
        with open(os.path.join(install, "MSIAfterburner.cfg"), "w", encoding="utf-8",
                  newline="") as f:
            f.write("[Startup]\nFormat=2\nMSIAfterburner.cfg")
    return install
