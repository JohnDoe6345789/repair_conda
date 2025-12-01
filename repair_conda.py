#!/usr/bin/env python3
"""
repair_miniconda_cookiecutter.py

Fixes the common Chocolatey miniconda3 path issue on Windows:

    did not find executable at 'C:\\miniconda3\\python.exe'

Cause:
    Many tools (e.g. cookiecutter) expect Miniconda at C:\\miniconda3,
    but Chocolatey installs Miniconda under:
        C:\\tools\\miniconda3

Fix:
    Create a directory junction:
        C:\\miniconda3  ->  C:\\tools\\miniconda3

This preserves compatibility without moving anything.

Features:
    • Logging (console output through Python logging module)
    • Dry-run by default
    • Diagnostics for Python, cookiecutter, and filesystem layout
    • Safe junction creation (requires admin)

Usage:
    python repair_miniconda_cookiecutter.py
    python repair_miniconda_cookiecutter.py --apply
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logger = logging.getLogger("miniconda_repair")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess."""
    logger.debug(f"Executing: {cmd}")
    return subprocess.run(cmd, capture_output=True, text=True)


def path_exists_description(path: Path) -> str:
    if path.exists():
        return f"exists ({'junction' if path.is_dir() else 'file/dir'})"
    return "missing"


def get_cookiecutter_path() -> str:
    """Return the resolved cookiecutter path if available."""
    result = run(["where", "cookiecutter"])
    if result.returncode == 0:
        return result.stdout.strip()
    return "not found"


def create_junction(target: Path, link: Path) -> bool:
    """
    Create NTFS junction: link -> target.
    Returns True if created successfully.
    """
    if link.exists():
        logger.error(f"Cannot create junction: {link} already exists.")
        return False

    cmd = ["cmd", "/c", "mklink", "/J", str(link), str(target)]
    result = run(cmd)
    if result.returncode == 0:
        logger.info(f"Created junction: {link} -> {target}")
        return True

    logger.error(f"mklink failed: {result.stderr}")
    return False


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--broken-root",
        default=r"C:\miniconda3",
        help="Path used by old shims (default: C:\\miniconda3)"
    )
    parser.add_argument(
        "--actual-root",
        default=None,
        help="Real miniconda install path (default: parent of sys.executable)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply repair (create junction)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    broken = Path(args.broken_root)
    actual = Path(args.actual_root) if args.actual_root else Path(sys.executable).parent

    logger.info("=== Miniconda Cookiecutter Path Repair Tool ===")
    logger.info(f"Running Python: {sys.executable}")
    logger.info(f"Expected broken root: {broken} [{path_exists_description(broken)}]")
    logger.info(f"Detected actual root: {actual} [{path_exists_description(actual)}]")

    cookie = get_cookiecutter_path()
    logger.info(f"cookiecutter resolved to: {cookie}")

    if not actual.exists():
        logger.error("Actual miniconda root does not exist. Cannot continue.")
        sys.exit(1)

    # If broken already points to actual, nothing to do
    if broken.exists():
        logger.info(f"{broken} already exists. Not modifying.")
        return

    if not args.apply:
        logger.info("")
        logger.info("Dry-run mode. No changes made.")
        logger.info("Use --apply to create:")
        logger.info(f"    mklink /J {broken} {actual}")
        return

    logger.info("Creating junction...")
    ok = create_junction(actual, broken)
    if not ok:
        sys.exit(1)

    logger.info("Repair complete.")
    logger.info("Try running: cookiecutter")


if __name__ == "__main__":
    main()
