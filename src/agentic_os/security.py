from dataclasses import dataclass
import os
from pathlib import Path
import re


SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    "secrets.json",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
SECRET_PATTERN = re.compile(
    "|".join(
        [
            r"\bsk-(?:live|test)?_?[A-Za-z0-9_-]{20,}\b",
            r"\bgithub_pat_[A-Za-z0-9_]{20,}\b",
            r"\bghp_[A-Za-z0-9]{20,}\b",
            r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
            (
                r"\b(?:"
                r"OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|"
                r"GITHUB_TOKEN|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|"
                r"STRIPE_SECRET_KEY|SUPABASE_SERVICE_ROLE_KEY|SLACK_BOT_TOKEN|"
                r"[A-Z][A-Z0-9_]*(?:_API_KEY|_AUTH_TOKEN|_BOT_TOKEN|_SECRET_KEY|_PRIVATE_KEY|_PASSWORD)|"
                r"PRIVATE_KEY|PASSWORD"
                r")\s*[:=]"
            ),
        ]
    )
)
LOCAL_PATH_PATTERN = re.compile(
    "|".join(
        [
            r"(?<![\w.-])(?:/Users/|/private/var/|/var/folders/|/tmp/)[^\s'\"`)]+",
            r"(?<![\w.-])[A-Za-z]:[\\/]+Users[\\/][^\s'\"`)]+",
            r"(?<![\w.-])%USERPROFILE%[\\/][^\s'\"`)]+",
            r"(?<![\w.-])\$env:USERPROFILE[\\/][^\s'\"`)]+",
        ]
    )
)
PRIVATE_MEMORY_REFERENCE_PATTERN = re.compile(
    r"(?<![\w.-])(?:\.agentic-os/)?memory/"
    r"(?:project-state|sessions|decisions|index(?:\.[A-Za-z0-9]+)?)[^\s'\"`)]+"
)
PRIVATE_MEMORY_REFERENCE_SUFFIXES = {".md", ".markdown", ".txt"}


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    path: str
    message: str
    line: int | None = None


def scan_private_data(paths: list[Path]) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []

    for candidate in scan_regular_files(paths):
        if candidate.name in SENSITIVE_FILENAMES:
            findings.append(
                SecurityFinding(
                    "SENSITIVE_FILENAME",
                    str(candidate),
                    f"Sensitive filename detected: {candidate.name}",
                )
            )

        try:
            content = candidate.read_bytes()
        except OSError:
            continue

        if b"\x00" in content:
            continue

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if SECRET_PATTERN.search(line):
                findings.append(
                    SecurityFinding(
                        "SECRET_PATTERN",
                        str(candidate),
                        "Potential secret pattern detected",
                        line_number,
                    )
                )
            if LOCAL_PATH_PATTERN.search(line):
                findings.append(
                    SecurityFinding(
                        "LOCAL_PATH_PATTERN",
                        str(candidate),
                        "Local filesystem path pattern detected",
                        line_number,
                    )
                )
            if (
                should_scan_private_memory_reference(candidate)
                and PRIVATE_MEMORY_REFERENCE_PATTERN.search(line)
            ):
                findings.append(
                    SecurityFinding(
                        "PRIVATE_MEMORY_REFERENCE",
                        str(candidate),
                        "Private project memory reference detected",
                        line_number,
                    )
                )

    return findings


def scan_regular_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        candidate = Path(path)
        if candidate.is_symlink() or not candidate.exists():
            continue
        if candidate.is_dir():
            for root, dirnames, filenames in os.walk(candidate):
                root_path = Path(root)
                dirnames[:] = [
                    dirname for dirname in dirnames if not (root_path / dirname).is_symlink()
                ]
                for filename in filenames:
                    child = root_path / filename
                    if child.is_symlink() or not child.is_file():
                        continue
                    files.append(child)
            continue
        if candidate.is_file():
            files.append(candidate)
    return files


def should_scan_private_memory_reference(path: Path) -> bool:
    return path.suffix.lower() in PRIVATE_MEMORY_REFERENCE_SUFFIXES
