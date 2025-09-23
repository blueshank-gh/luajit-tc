import os
import shutil
import subprocess
from typing import Optional

def find() -> Optional[str]:
    env = os.getenv("GDB_PATH")
    if env and shutil.which(env):
        return env

    gdb = shutil.which("gdb")
    if gdb:
        return gdb

    for p in ["/usr/bin/gdb", "/usr/local/bin/gdb"]:
        if os.path.exists(p):
            return p

    return None