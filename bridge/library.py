"""UberGuidoZ/Flipper file library integration.

The community-standard all-in-one Flipper Zero file collection
(https://github.com/UberGuidoZ/Flipper — 17k+ stars): apps, BadUSB, IR,
SubGHz, NFC, RFID, music, and more.

We do NOT vendor the repo (it's gigabytes). Files are fetched on demand
from GitHub and cached locally; nothing is re-downloaded while cached.
Installs go to the correct SD card paths on the Flipper.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

REPO = "UberGuidoZ/Flipper"
REPO_URL = f"https://github.com/{REPO}"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
API_TREE = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"

CACHE_DIR = os.path.expanduser("~/.flipper-brain/library-cache")
TREE_CACHE = os.path.join(CACHE_DIR, "tree.json")
TREE_TTL_S = 24 * 3600
MAX_FILE_BYTES = 8 * 1024 * 1024  # refuse anything bigger than 8 MB

# repo top-level category -> (Flipper SD dir, one-click installable?, note)
CATEGORIES: dict[str, tuple[str | None, bool, str]] = {
    "Applications": ("/ext/apps", True, ".fap apps"),
    "BadUSB": ("/ext/badusb", True, "DuckyScript payloads (text, inspect before use)"),
    "Infrared": ("/ext/infrared", True, ".ir remote files"),
    "Sub-GHz": ("/ext/subghz", True, ".sub captures — RX reference only"),
    "NFC": ("/ext/nfc", True, ".nfc dumps"),
    "RFID": ("/ext/lfrfid", True, "125 kHz RFID files"),
    "Music_Player": ("/ext/music", True, "music files"),
    "Wav_Player": ("/ext/wav_player", True, ".wav files (verify on-device)"),
    "unirf": ("/ext/unirf", True, "UniRF remotes (verify on-device)"),
    "subplaylist": ("/ext/subghz", True, "SubGHz playlists"),
    "picopass": ("/ext/picopass", True, "picopass files (verify on-device)"),
    "iButton": ("/ext/ibutton", True, "iButton keys"),
    "GPIO": (None, False, "docs/diagrams — browse only"),
    "Graphics": (None, False, "asset packs — manual install"),
    "Dolphin_Level": (None, False, "XP files — browse only"),
    "Firmware_Options": (None, False, "firmware configs — browse only"),
    "Hardware_Troubleshooting": (None, False, "docs — browse only"),
    "FlipperZero_Dimensions": (None, False, "docs — browse only"),
    "Wifi_DevBoard": (None, False, "dev-board files — browse only"),
    "wetox_scripts": (None, False, "scripts — browse only"),
}


class LibraryError(Exception):
    pass


def _safe_repo_path(repo_path: str) -> str:
    """Validate a repo-relative path. Rejects absolute paths, '.'/'..'
    segments, and empty segments — prevents both SD-card traversal
    (/ext/apps/../../int) and cache-dir escape (../../evil)."""
    p = (repo_path or "").strip().lstrip("/")
    parts = p.split("/")
    if not p or any(seg in ("", ".", "..") for seg in parts):
        raise LibraryError(f"invalid repo path {repo_path!r}")
    return p


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "neuroflipper/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise LibraryError(f"HTTP {resp.status} for {url}")
        length = resp.headers.get("Content-Length")
        if length and int(length) > MAX_FILE_BYTES:
            raise LibraryError(f"file too large ({length} bytes)")
        data = resp.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise LibraryError("file too large (>8 MB)")
    return data


def get_tree(refresh: bool = False) -> list[dict]:
    """Full recursive file tree of the repo (cached 24h). Returns entries."""
    if not refresh and os.path.exists(TREE_CACHE):
        try:
            age = time.time() - os.path.getmtime(TREE_CACHE)
            if age < TREE_TTL_S:
                with open(TREE_CACHE) as fh:
                    return json.load(fh)["tree"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            pass  # corrupt cache -> fall through and re-fetch
    try:
        data = _get(API_TREE, timeout=60)
    except Exception as exc:
        raise LibraryError(f"couldn't fetch repo tree: {exc}")
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LibraryError(f"repo tree isn't valid JSON: {exc}")
    tree = [e for e in payload.get("tree", []) if e.get("type") == "blob"]
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = TREE_CACHE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"fetched": time.time(), "tree": tree}, fh)
    os.replace(tmp, TREE_CACHE)
    return tree


def categories() -> list[dict]:
    return [{"name": k, "sd_path": v[0], "installable": v[1], "note": v[2]}
            for k, v in CATEGORIES.items()]


def list_category(category: str, subpath: str = "") -> list[dict]:
    """List files directly under a category[/subpath]."""
    prefix = category + ("/" + subpath.strip("/") if subpath else "") + "/"
    out = []
    for e in get_tree():
        p = e["path"]
        if p.startswith(prefix):
            rest = p[len(prefix):]
            if "/" not in rest:  # direct child file
                out.append({"path": p, "name": rest, "size": e.get("size", 0)})
    return sorted(out, key=lambda x: x["name"].lower())


def search(query: str, limit: int = 50) -> list[dict]:
    q = query.lower()
    hits = []
    for e in get_tree():
        if q in e["path"].lower():
            hits.append({"path": e["path"], "size": e.get("size", 0)})
            if len(hits) >= limit:
                break
    return hits


def cached_path(repo_path: str) -> str:
    return os.path.join(CACHE_DIR, "files", _safe_repo_path(repo_path))


def download(repo_path: str) -> str:
    """Fetch a repo file to the local cache. Returns local path.
    Never re-downloads while cached."""
    repo_path = _safe_repo_path(repo_path)
    local = cached_path(repo_path)
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return local
    try:
        data = _get(f"{RAW_BASE}/{repo_path}")
    except Exception as exc:
        raise LibraryError(f"couldn't download {repo_path}: {exc}")
    os.makedirs(os.path.dirname(local), exist_ok=True)
    tmp = local + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, local)
    return local


def sd_path_for(repo_path: str) -> str:
    """Map a repo path to its Flipper SD destination. Raises if browse-only."""
    repo_path = _safe_repo_path(repo_path)
    top = repo_path.split("/")[0]
    if top not in CATEGORIES:
        raise LibraryError(f"unknown category {top!r}")
    sd_dir, installable, _ = CATEGORIES[top]
    if not installable or not sd_dir:
        raise LibraryError(f"{top} is browse-only (see category note)")
    rest = "/".join(repo_path.split("/")[1:])
    return f"{sd_dir}/{rest}"


def install(flipper, repo_path: str) -> dict:
    """Download (cached) + push a library file to the Flipper SD card.
    Returns {repo_path, sd_path, bytes}."""
    sd_path = sd_path_for(repo_path)  # validates installability first
    local = download(repo_path)
    with open(local, "rb") as fh:
        data = fh.read()
    flipper.ensure_dir(sd_path)
    if repo_path.lower().endswith(".fap"):
        flipper.storage_write_bytes(sd_path, data)
    else:
        # Text-ish payloads go through as bytes too — byte-exact, no mangling.
        flipper.storage_write_bytes(sd_path, data)
    return {"repo_path": repo_path, "sd_path": sd_path, "bytes": len(data)}
