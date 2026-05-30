from __future__ import annotations

import re
from collections.abc import Iterable

from .schemas import ChangedFile, HunkLine

HUNK_RE = re.compile(r"@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@")


def iter_hunk_lines(changed_file: ChangedFile) -> Iterable[HunkLine]:
    """Yield parsed patch lines with best-effort old/new line numbers."""
    if not changed_file.patch:
        return

    new_line = None
    old_line = None
    hunk_header = ""

    for raw_line in changed_file.patch.splitlines():
        match = HUNK_RE.search(raw_line)
        if match:
            old_line = int(match.group("old_start"))
            new_line = int(match.group("new_start"))
            hunk_header = raw_line
            continue

        if new_line is None or old_line is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            yield HunkLine(
                filename=changed_file.filename,
                line_no=new_line,
                old_line_no=None,
                kind="added",
                text=raw_line[1:],
                hunk_header=hunk_header,
            )
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            yield HunkLine(
                filename=changed_file.filename,
                line_no=None,
                old_line_no=old_line,
                kind="removed",
                text=raw_line[1:],
                hunk_header=hunk_header,
            )
            old_line += 1
        else:
            text = raw_line[1:] if raw_line.startswith(" ") else raw_line
            yield HunkLine(
                filename=changed_file.filename,
                line_no=new_line,
                old_line_no=old_line,
                kind="context",
                text=text,
                hunk_header=hunk_header,
            )
            new_line += 1
            old_line += 1


def added_lines(changed_file: ChangedFile) -> list[HunkLine]:
    return [line for line in iter_hunk_lines(changed_file) if line.kind == "added"]


def truncate_patch(files: list[ChangedFile], max_chars: int) -> str:
    chunks: list[str] = []
    remaining = max_chars

    for file in files:
        header = (
            f"\n--- {file.filename} "
            f"({file.status}, +{file.additions}/-{file.deletions}) ---\n"
        )
        patch = file.patch or "[No textual patch available]"
        block = header + patch
        if len(block) > remaining:
            if remaining > len(header) + 200:
                chunks.append(header + patch[: remaining - len(header)] + "\n[Patch truncated]")
            break
        chunks.append(block)
        remaining -= len(block)

    return "".join(chunks).strip()


def is_generated_or_lock_file(path: str) -> bool:
    lower = path.lower()
    generated_suffixes = (
        ".min.js",
        ".map",
        ".lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "uv.lock",
    )
    generated_dirs = ("/dist/", "/build/", "/vendor/", "/generated/")
    return lower.endswith(generated_suffixes) or any(
        marker in f"/{lower}" for marker in generated_dirs
    )
