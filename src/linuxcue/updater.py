from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from . import __version__

try:
    from .build_info import __commit__ as BUILD_COMMIT
    from .build_info import __repo__ as BUILD_REPO
except Exception:  # pragma: no cover - build metadata is optional
    BUILD_COMMIT = ""
    BUILD_REPO = "Maggi0r/Linuxcue"

DEFAULT_REPO = BUILD_REPO or "Maggi0r/Linuxcue"
GITHUB_API = "https://api.github.com"


def _github_json(path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{GITHUB_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "linuxcue-updater",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _github_json_or_none(path: str) -> dict[str, Any] | None:
    try:
        return _github_json(path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value.lstrip("vV"))
    return tuple(int(part) for part in parts[:4]) or (0,)


def _is_newer_version(latest: str, current: str) -> bool:
    return _version_tuple(latest) > _version_tuple(current)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def current_commit() -> str:
    if BUILD_COMMIT:
        return BUILD_COMMIT
    git = shutil.which("git")
    if not git:
        return ""
    try:
        result = subprocess.run(
            [git, "-C", str(_project_root()), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return result.stdout.strip()


def check_github_update(repo: str = DEFAULT_REPO) -> dict[str, Any]:
    repo = (repo or DEFAULT_REPO).strip()
    repo_info = _github_json(f"/repos/{repo}")
    default_branch = str(repo_info.get("default_branch") or "main")
    release = _github_json_or_none(f"/repos/{repo}/releases/latest")
    commit = _github_json(f"/repos/{repo}/commits/{default_branch}")

    installed_commit = current_commit()
    latest_sha = str(commit.get("sha") or "")
    latest_tag = str((release or {}).get("tag_name") or "")
    release_update = bool(latest_tag and _is_newer_version(latest_tag, __version__))
    source_update: bool | None
    if installed_commit and latest_sha:
        source_update = not latest_sha.startswith(installed_commit[:12])
    elif latest_sha:
        source_update = None
    else:
        source_update = False

    commit_payload = commit.get("commit") if isinstance(commit.get("commit"), dict) else {}
    author_payload = commit_payload.get("author") if isinstance(commit_payload.get("author"), dict) else {}
    latest_commit = {
        "sha": latest_sha,
        "short_sha": latest_sha[:7],
        "date": author_payload.get("date", ""),
        "message": str(commit_payload.get("message") or "").splitlines()[0],
        "html_url": commit.get("html_url", ""),
    }
    latest_release = None
    if release:
        latest_release = {
            "tag": latest_tag,
            "name": release.get("name") or latest_tag,
            "published_at": release.get("published_at", ""),
            "html_url": release.get("html_url", ""),
        }

    update_available = release_update or source_update is True
    if release_update:
        recommendation = f"Release {latest_tag} ist neuer als installierte Version {__version__}."
    elif source_update is True:
        recommendation = f"GitHub-Code ist neuer als die installierte Revision {installed_commit[:7]}."
    elif source_update is None:
        recommendation = "Installierte Git-Revision ist unbekannt; GitHub-Code konnte nur als Referenz geprueft werden."
    else:
        recommendation = "linuxcue ist aktuell."

    return {
        "repo": repo,
        "default_branch": default_branch,
        "current_version": __version__,
        "current_commit": installed_commit,
        "latest_release": latest_release,
        "latest_commit": latest_commit,
        "release_update_available": release_update,
        "source_update_available": source_update,
        "update_available": update_available,
        "recommendation": recommendation,
    }


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Benoetigtes Programm nicht gefunden: {name}")
    return path


def install_update_from_github(repo: str = DEFAULT_REPO, *, yes: bool = False, cache_dir: str | None = None) -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("Automatische Installation ist nur auf Linux/CachyOS vorgesehen.")

    git = _require_binary("git")
    bash = _require_binary("bash")
    _require_binary("pacman")

    repo = (repo or DEFAULT_REPO).strip()
    if not yes and sys.stdin.isatty():
        answer = input(f"linuxcue aus https://github.com/{repo} aktualisieren und installieren? [y/N] ")
        if answer.strip().casefold() not in {"y", "yes", "j", "ja"}:
            return {"installed": False, "cancelled": True, "repo": repo}

    info = check_github_update(repo)
    default_branch = str(info.get("default_branch") or "main")
    target = Path(cache_dir or "~/.cache/linuxcue/source").expanduser()
    repo_url = f"https://github.com/{repo}.git"

    if (target / ".git").exists():
        subprocess.run([git, "-C", str(target), "remote", "set-url", "origin", repo_url], check=True)
        subprocess.run([git, "-C", str(target), "fetch", "--tags", "origin"], check=True)
        subprocess.run([git, "-C", str(target), "reset", "--hard", f"origin/{default_branch}"], check=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([git, "clone", repo_url, str(target)], check=True)

    subprocess.run([bash, "scripts/install-cachyos-package.sh"], cwd=target, check=True)
    installed_commit = subprocess.run(
        [git, "-C", str(target), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "installed": True,
        "repo": repo,
        "source_dir": str(target),
        "branch": default_branch,
        "installed_commit": installed_commit,
        "previous_check": info,
    }
