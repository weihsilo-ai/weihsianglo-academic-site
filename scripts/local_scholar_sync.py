#!/usr/bin/env python3
"""Install and run a non-resident macOS Scholar sync job."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import plistlib
import pwd
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


LABEL = "com.weihsilo.academic-site-scholar-sync"
REMOTE_URL = "https://github.com/weihsilo-ai/weihsianglo-academic-site.git"
USER_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
APP_DIR = USER_HOME / "Library" / "Application Support" / "AcademicSiteScholarSync"
REPO_DIR = APP_DIR / "repo"
INSTALLED_SCRIPT = APP_DIR / "local_scholar_sync.py"
PLIST_PATH = USER_HOME / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_PATH = USER_HOME / "Library" / "Logs" / "AcademicSiteScholarSync.log"
LOCK_PATH = APP_DIR / "sync.lock"
GIT = "/usr/bin/git"


def build_launch_agent(
    *,
    python_executable: str,
    installed_script: Path,
    log_path: Path,
) -> dict[str, object]:
    return {
        "Label": LABEL,
        "ProgramArguments": [python_executable, "-u", str(installed_script), "--run"],
        "RunAtLoad": True,
        "StartCalendarInterval": {"Hour": 9, "Minute": 0},
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(log_path),
        "StandardErrorPath": str(log_path),
    }


def synced_on_date(publications_path: Path, expected_date: dt.date) -> bool:
    try:
        payload = json.loads(publications_path.read_text(encoding="utf-8"))
        timestamp = payload["source"]["last_successful_sync_at"]
        synced_at = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return synced_at.date() == expected_date


def run_command(args: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(args)}", flush=True)
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


@contextmanager
def single_instance_lock() -> Iterator[bool]:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            stale = time.time() - LOCK_PATH.stat().st_mtime > 7200
        except OSError:
            stale = False
        if not stale:
            yield False
            return
        LOCK_PATH.unlink(missing_ok=True)
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)

    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield True
    finally:
        LOCK_PATH.unlink(missing_ok=True)


def ensure_repository() -> None:
    if not (REPO_DIR / ".git").exists():
        APP_DIR.mkdir(parents=True, exist_ok=True)
        run_command([GIT, "clone", "--branch", "main", "--single-branch", REMOTE_URL, str(REPO_DIR)])
        run_command([GIT, "config", "user.name", "local-scholar-sync"], cwd=REPO_DIR)
        run_command([GIT, "config", "user.email", "local-scholar-sync@users.noreply.github.com"], cwd=REPO_DIR)
        return

    dirty = run_command([GIT, "status", "--porcelain"], cwd=REPO_DIR, capture=True).stdout.strip()
    if dirty:
        raise RuntimeError(f"Dedicated sync clone is not clean:\n{dirty}")

    run_command([GIT, "fetch", "origin", "main"], cwd=REPO_DIR)
    ahead_behind = run_command(
        [GIT, "rev-list", "--left-right", "--count", "origin/main...HEAD"],
        cwd=REPO_DIR,
        capture=True,
    ).stdout.split()
    behind, ahead = (int(value) for value in ahead_behind)

    if behind and ahead:
        raise RuntimeError("Dedicated sync clone diverged from origin/main; refusing to rewrite history.")
    if ahead:
        run_command([GIT, "push", "origin", "HEAD:main"], cwd=REPO_DIR)
    if behind:
        run_command([GIT, "merge", "--ff-only", "origin/main"], cwd=REPO_DIR)


def run_sync() -> None:
    with single_instance_lock() as acquired:
        if not acquired:
            print("Another Scholar sync is already running; exiting.", flush=True)
            return

        ensure_repository()
        publications_path = REPO_DIR / "data" / "publications.json"
        today = dt.datetime.now(dt.timezone.utc).date()
        if synced_on_date(publications_path, today):
            print(f"Scholar data is already current for {today.isoformat()}; exiting.", flush=True)
            return

        status_path = APP_DIR / "status.json"
        run_command(
            [
                sys.executable,
                "scripts/publications_pipeline.py",
                "sync-scholar",
                "--status-json",
                str(status_path),
            ],
            cwd=REPO_DIR,
        )

        diff = subprocess.run([GIT, "diff", "--quiet", "--", "data/publications.json"], cwd=REPO_DIR)
        if diff.returncode == 0:
            print("Scholar sync produced no publication changes; exiting.", flush=True)
            return
        if diff.returncode != 1:
            raise RuntimeError(f"git diff failed with exit code {diff.returncode}")

        run_command([GIT, "add", "data/publications.json"], cwd=REPO_DIR)
        run_command([GIT, "commit", "-m", "Update Google Scholar publications"], cwd=REPO_DIR)
        run_command([GIT, "push", "origin", "HEAD:main"], cwd=REPO_DIR)
        print("Scholar data was updated and pushed successfully.", flush=True)


def install_launch_agent() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), INSTALLED_SCRIPT)

    payload = build_launch_agent(
        python_executable=sys.executable,
        installed_script=INSTALLED_SCRIPT,
        log_path=LOG_PATH,
    )
    temporary_plist = PLIST_PATH.with_suffix(".plist.tmp")
    with temporary_plist.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)
    os.replace(temporary_plist, PLIST_PATH)

    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["/bin/launchctl", "bootout", f"{domain}/{LABEL}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run_command(["/bin/launchctl", "bootstrap", domain, str(PLIST_PATH)])
    run_command(["/bin/launchctl", "kickstart", "-k", f"{domain}/{LABEL}"])
    print(f"Installed {LABEL}. It runs at login and daily at 09:00 local time.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true", help="Install and start the user LaunchAgent.")
    action.add_argument("--run", action="store_true", help="Run one Scholar sync attempt.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.install:
        install_launch_agent()
    else:
        run_sync()


if __name__ == "__main__":
    main()
