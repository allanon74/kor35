import os
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def get_build_info():
    """
    Restituisce informazioni di build/runtime per debug e admin.

    Fonte primaria: variabili d'ambiente (iniettate dal deploy/CI).
    Fallback: git (solo se disponibile sul server).
    """
    env_version = (os.getenv("KOR35_BUILD_VERSION") or "").strip()
    env_sha = (os.getenv("KOR35_BUILD_SHA") or "").strip()
    env_time = (os.getenv("KOR35_BUILD_TIME") or "").strip()
    env_env = (os.getenv("ENVIRONMENT") or "").strip()

    version = env_version
    sha = env_sha

    if not version or not sha:
        try:
            sha_full = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
            sha_short = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
            dirty = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
            is_dirty = bool(dirty)
            sha = sha or sha_full
            version = version or (f"g{sha_short}{'-dirty' if is_dirty else ''}")
        except Exception:
            # Git non disponibile: lasciamo i fallback "unknown"
            pass

    return {
        "version": version or "unknown",
        "sha": sha or "unknown",
        "time": env_time or "",
        "environment": env_env or "",
    }

