#!/usr/bin/env python3
"""Secret and Personal Data Scanner for ghostreply.

Performs:
1. Gitleaks scan (if gitleaks binary is present).
2. Phone-number pattern check (regex for international phone numbers).
3. Local real-name sweep using uncommitted .local-denylist (if present).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PHONE_REGEX = re.compile(r"(\+?\b\d{10,15}\b)")

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".enc",
    ".sqlite",
    ".db",
    ".bin",
    ".lock",
}

ALLOWED_PHONE_TEMPLATES = {
    "about_me.example.md",
    "schedule.example.json",
    ".env.example",
}


def load_local_denylist(root: Path) -> list[str]:
    denylist_file = root / ".local-denylist"
    if not denylist_file.is_file():
        return []
    with open(denylist_file, "r", encoding="utf-8", errors="ignore") as fp:
        lines = [line.strip() for line in fp if line.strip() and not line.startswith("#")]
    return [name for name in lines if len(name) >= 3]


def scan_file(file_path: Path, denylist: list[str]) -> list[dict]:
    findings = []
    if file_path.name in ALLOWED_PHONE_TEMPLATES:
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fp:
            for line_no, line in enumerate(fp, start=1):
                # Check phone numbers
                for match in PHONE_REGEX.finditer(line):
                    val = match.group(0)
                    # Exclude common port/timestamp/hash false positives
                    if not (val.startswith("2026") or val.startswith("127001")):
                        findings.append({
                            "type": "phone_pattern",
                            "file": str(file_path),
                            "line": line_no,
                        })
                # Check real names from local denylist
                for name in denylist:
                    if re.search(r"(?i)\b" + re.escape(name) + r"\b", line):
                        findings.append({
                            "type": "denylisted_name",
                            "file": str(file_path),
                            "line": line_no,
                        })
    except Exception:
        pass
    return findings


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    denylist = load_local_denylist(root)

    print("=== ghostreply Secret & Privacy Scan ===")

    # 1. Gitleaks execution
    gitleaks_bin = shutil.which("gitleaks")
    if gitleaks_bin:
        print("[1/2] Running Gitleaks scan...")
        res = subprocess.run([gitleaks_bin, "dir", "--no-banner", str(root)])
        if res.returncode != 0:
            print("ERROR: Gitleaks detected secrets!")
            return 1
        print("PASS: Gitleaks reported 0 leaks.")
    else:
        print("[1/2] Gitleaks binary not found in PATH; skipping binary run.")

    # 2. Pattern and denylist scan
    print("[2/2] Scanning files for phone patterns and personal data...")
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if file_path.suffix in IGNORED_EXTENSIONS:
                continue
            findings.extend(scan_file(file_path, denylist))

    if findings:
        print(f"FAILED: Found {len(findings)} sensitive pattern matches:")
        for f in findings:
            print(f"  - [{f['type']}] {f['file']}:{f['line']}")
        return 1

    print("PASS: 0 phone patterns and 0 denylisted entries detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
