"""Release audit for public repository hygiene.

This is a maintainer-side guardrail. It does not implement product privacy
features; it only prevents accidental publication of local secrets, internal
addresses, or real clinical identifiers in this repository.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Finding:
    path: Path
    line_no: int
    label: str
    text: str


PATTERNS = [
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("GitHub token", re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private IPv4 address", re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")),
    ("Chinese national ID", re.compile(r"(?<!\d)[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
    ("Chinese mobile phone", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("Internal hospital/project term", re.compile(r"(环湖|内网|真实患者|患者姓名|身份证号|住院号)")),
]

ALLOWLIST_PATTERNS = [
    re.compile(r"api_key: str = \"\""),
    re.compile(r"API Key，可留空"),
    re.compile(r"API key should not be committed", re.I),
    re.compile(r"住院号：A123456"),
    re.compile(r"Internal hospital/project term"),
]

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "dist", "build"}


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if set(path.parts) & SKIP_DIRS:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def is_allowlisted(line: str) -> bool:
    return any(pattern.search(line) for pattern in ALLOWLIST_PATTERNS)


def scan_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings
    for line_no, line in enumerate(lines, start=1):
        if is_allowlisted(line):
            continue
        for label, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path=path, line_no=line_no, label=label, text=line.strip()))
    return findings


def main() -> int:
    findings: List[Finding] = []
    for path in iter_files(ROOT):
        findings.extend(scan_file(path))

    if findings:
        print("Release audit failed. Review these findings before publishing:\n")
        for finding in findings:
            rel = finding.path.relative_to(ROOT)
            print(f"- {rel}:{finding.line_no} [{finding.label}] {finding.text[:160]}")
        return 1

    print("Release audit passed: no obvious local secrets, private IPs, or real clinical identifiers found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
