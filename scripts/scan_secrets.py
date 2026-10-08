#!/usr/bin/env python3
"""Secret and Personal Data Scanner for ghostreply.

Performs:
1. Gitleaks scan (if gitleaks binary is present).
2. Separator-tolerant phone-number pattern check (spaces, dashes, parens, optional +).
   Explicit markers for fake test fixtures (e.g. FAKE_TEST_NUMBER, 555-01XX) are permitted.
3. Local real-name sweep using uncommitted .local-denylist (if present).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Matches candidates with optional country code, parentheses, spaces, dots, dashes
PHONE_CANDIDATE_REGEX = re.compile(
    r"(\+?\s*(?:\(\s*\d{1,4}\s*\)|\d{1,4})?[\s.-]*(?:\(?\s*\d{2,4}\s*\)?[\s.-]*){2,5}\d{2,4})"
)

# Explicit marker allowing fake test numbers in fixtures / tests
FAKE_NUMBER_MARKER = re.compile(
    r"(?i)(#\s*fake[-_]?test[-_]?number|FAKE_TEST_NUMBER|mock[-_]?phone|555[-_.]?01\d{2}|000[-_.]?0000|\+155501)"
)

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
                # Check for explicit fake marker
                has_fake_marker = bool(FAKE_NUMBER_MARKER.search(line))

                # Check phone candidates
                if not has_fake_marker:
                    for match in PHONE_CANDIDATE_REGEX.finditer(line):
                        raw_match = match.group(0)
                        digits = re.sub(r"\D", "", raw_match)
                        # Only flag if total digit count is between 10 and 15 digits
                        if 10 <= len(digits) <= 15:
                            # Filter obvious non-phone false positives (dates, loopback, ports)
                            if not (digits.startswith("2026") or digits.startswith("127001") or digits.startswith("0000000000")):
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
    if not gitleaks_bin:
        # Check standard winget install location on Windows
        winget_gitleaks = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        for p in winget_gitleaks.glob("**/gitleaks.exe"):
            gitleaks_bin = str(p)
            break

    if gitleaks_bin:
        print(f"[1/2] Running Gitleaks scan ({gitleaks_bin})...")
        res = subprocess.run([gitleaks_bin, "dir", "--no-banner", str(root)])
        if res.returncode != 0:
            print("ERROR: Gitleaks detected secrets!")
            return 1
        print("PASS: Gitleaks reported 0 leaks.")
    else:
        print("[1/2] Gitleaks binary not found in PATH; skipping binary run.")

    # 2. Pattern and denylist scan
    print("[2/2] Scanning files for separator-tolerant phone patterns and personal data...")
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
