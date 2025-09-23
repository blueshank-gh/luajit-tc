import os
import platform
import shutil
import subprocess
import sys
from typing import Optional

if os.name != "nt":
    raise RuntimeError("This module is Windows-only (cdb.exe is a Windows tool).")

try:
    import winreg
except Exception:
    winreg = None

COMMON_KITS_PATHS = [
    r"%ProgramFiles(x86)%\Windows Kits\10\Debuggers",
    r"%ProgramFiles(x86)%\Windows Kits\8.1\Debuggers",
    r"%ProgramFiles%\Windows Kits\10\Debuggers",
    r"%ProgramFiles%\Windows Kits\8.1\Debuggers",
]

def _expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))

def _exists(path: str) -> bool:
    return os.path.exists(path) and os.path.isfile(path)

def _try_registry_find_kitsroot():
    candidates = []
    if winreg is None:
        return candidates

    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows Kits\Installed Roots", ["KitsRoot10", "KitsRoot81"])
    ]
    
    try:
        for hive, keypath, names in roots:
            with winreg.OpenKey(hive, keypath) as k:
                for name in names:
                    try:
                        val, _ = winreg.QueryValueEx(k, name)
                        if val:
                            candidates.append(val)
                    except FileNotFoundError:
                        pass
    except Exception:
        pass
    return candidates

def find(prefer_bitness: Optional[str] = None) -> Optional[str]:
    env = os.getenv("CDB_PATH") or os.getenv("DEBUGGER_CDB_PATH")
    if env and _exists(env):
        return env

    which_path = shutil.which("cdb.exe")
    if which_path:
        return which_path

    try:
        out = subprocess.run(["where", "cdb.exe"], capture_output=True, text=True, check=False)
        if out.returncode == 0:
            for line in out.stdout.splitlines():
                p = line.strip()
                if _exists(p):
                    return p
    except Exception:
        pass

    if prefer_bitness not in ("x86", "x64", None):
        raise ValueError("prefer_bitness must be 'x86', 'x64', or None")

    if prefer_bitness is None:
        prefer_bitness = "x64" if sys.maxsize > 2**32 else "x86"

    candidate_paths = []

    for kitsroot in _try_registry_find_kitsroot():
        root = _expand(kitsroot)
        for arch in (prefer_bitness, "x64" if prefer_bitness == "x86" else "x86"):
            candidate_paths.append(os.path.join(root, "Debuggers", arch, "cdb.exe"))

    for base in COMMON_KITS_PATHS:
        base = _expand(base)
        for arch in (prefer_bitness, "x64" if prefer_bitness == "x86" else "x86"):
            candidate_paths.append(os.path.join(base, arch, "cdb.exe"))

    pf86 = os.environ.get("ProgramFiles(x86)")
    if pf86:
        candidate_paths.append(os.path.join(pf86, "Windows Kits", "10", "Debuggers", "x64", "cdb.exe"))
        candidate_paths.append(os.path.join(pf86, "Windows Kits", "10", "Debuggers", "x86", "cdb.exe"))

    for p in candidate_paths:
        if p and _exists(p):
            return p

    return None