from __future__ import annotations

import hashlib
import re
from collections import Counter

from .diff_parser import added_lines, is_generated_or_lock_file
from .schemas import ChangedFile, ReviewCategory, ReviewFinding, Severity

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"
)
SQL_RE = re.compile(r"(?i)(select|insert|update|delete)\s+.+(\+|f['\"]|format\(|%s)")
SHELL_RE = re.compile(r"(?i)(subprocess\.(popen|call|run)|os\.system|exec\()\s*\(")
BROAD_EXCEPT_RE = re.compile(r"^\s*except\s*(Exception|BaseException)?\s*:")
TODO_RE = re.compile(r"(?i)\b(todo|fixme|hack)\b")
AUTH_PATH_RE = re.compile(r"(?i)(auth|login|permission|policy|role|jwt|oauth|session)")
MIGRATION_RE = re.compile(r"(?i)(migration|schema|ddl|alembic|liquibase)")
TEST_PATH_RE = re.compile(r"(^|/)(test|tests|spec|__tests__)(/|_)|(_test|\.spec)\.")
DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "pom.xml",
    "build.gradle",
    "go.mod",
    "cargo.toml",
}


def _fingerprint(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _finding(
    *,
    title: str,
    body: str,
    severity: Severity,
    category: ReviewCategory,
    confidence: float,
    file_path: str | None,
    line: int | None,
    evidence: str | None,
    recommendation: str,
    source: str = "heuristic",
) -> ReviewFinding:
    return ReviewFinding(
        title=title,
        body=body,
        severity=severity,
        category=category,
        confidence=confidence,
        file_path=file_path,
        line=line,
        evidence=evidence.strip() if evidence else None,
        recommendation=recommendation,
        source=source,
        fingerprint=_fingerprint(title, file_path, line, evidence),
    )


class HeuristicAnalyzer:
    def analyze(self, files: list[ChangedFile]) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        findings.extend(self._scan_lines(files))
        findings.extend(self._scan_file_level(files))
        return self._dedupe(findings)

    def _scan_lines(self, files: list[ChangedFile]) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []

        for file in files:
            if is_generated_or_lock_file(file.filename):
                continue

            for line in added_lines(file):
                text = line.text
                if SECRET_RE.search(text):
                    findings.append(
                        _finding(
                            title="Possible hard-coded secret",
                            body=(
                                "A newly added line looks like it may contain a credential "
                                "or secret value."
                            ),
                            severity=Severity.critical,
                            category=ReviewCategory.security,
                            confidence=0.88,
                            file_path=file.filename,
                            line=line.line_no,
                            evidence=text,
                            recommendation=(
                                "Move the value to a secret manager or environment variable, "
                                "rotate it if it was real, and add a regression check to "
                                "prevent committing secrets."
                            ),
                        )
                    )

                if SQL_RE.search(text):
                    findings.append(
                        _finding(
                            title="Possible SQL injection risk",
                            body=(
                                "The change appears to build SQL with string interpolation "
                                "or concatenation."
                            ),
                            severity=Severity.high,
                            category=ReviewCategory.security,
                            confidence=0.72,
                            file_path=file.filename,
                            line=line.line_no,
                            evidence=text,
                            recommendation=(
                                "Use parameterized queries or a query builder with bound "
                                "parameters."
                            ),
                        )
                    )

                if SHELL_RE.search(text) and (
                    "shell=True" in text or "+" in text or "format(" in text
                ):
                    findings.append(
                        _finding(
                            title="Dangerous command execution pattern",
                            body=(
                                "A command execution call appears to include shell usage "
                                "or dynamic command text."
                            ),
                            severity=Severity.high,
                            category=ReviewCategory.security,
                            confidence=0.7,
                            file_path=file.filename,
                            line=line.line_no,
                            evidence=text,
                            recommendation=(
                                "Pass arguments as a list, avoid `shell=True`, and validate "
                                "any user-controlled values before execution."
                            ),
                        )
                    )

                if BROAD_EXCEPT_RE.search(text):
                    findings.append(
                        _finding(
                            title="Broad exception handling",
                            body=(
                                "The change catches a broad exception, which can hide "
                                "failures and complicate debugging."
                            ),
                            severity=Severity.medium,
                            category=ReviewCategory.reliability,
                            confidence=0.68,
                            file_path=file.filename,
                            line=line.line_no,
                            evidence=text,
                            recommendation=(
                                "Catch a narrower exception type and log or re-raise "
                                "unexpected failures."
                            ),
                        )
                    )

                if TODO_RE.search(text):
                    findings.append(
                        _finding(
                            title="New TODO-style marker",
                            body=(
                                "The PR adds a TODO/FIXME/HACK marker that may represent "
                                "unfinished work."
                            ),
                            severity=Severity.low,
                            category=ReviewCategory.maintainability,
                            confidence=0.6,
                            file_path=file.filename,
                            line=line.line_no,
                            evidence=text,
                            recommendation=(
                                "Confirm whether this should be resolved before merge or "
                                "tracked in an issue."
                            ),
                        )
                    )

        return findings

    def _scan_file_level(self, files: list[ChangedFile]) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        changed_paths = [file.filename for file in files]
        path_counter = Counter(path.split("/", 1)[0] for path in changed_paths)
        total_changes = sum(file.changes for file in files)
        has_tests = any(TEST_PATH_RE.search(path) for path in changed_paths)

        if total_changes > 800:
            findings.append(
                _finding(
                    title="Large PR requires focused review plan",
                    body=f"This PR changes {total_changes} lines across {len(files)} files.",
                    severity=Severity.medium,
                    category=ReviewCategory.maintainability,
                    confidence=0.82,
                    file_path=None,
                    line=None,
                    evidence=f"{len(files)} files, {total_changes} changed lines",
                    recommendation=(
                        "Consider splitting independent work or adding a reviewer "
                        "checklist that identifies the highest-risk files."
                    ),
                )
            )

        if not has_tests and any(not is_generated_or_lock_file(path) for path in changed_paths):
            findings.append(
                _finding(
                    title="No test changes detected",
                    body=(
                        "The PR changes implementation files but does not appear to add "
                        "or update tests."
                    ),
                    severity=Severity.medium,
                    category=ReviewCategory.testing,
                    confidence=0.65,
                    file_path=None,
                    line=None,
                    evidence=", ".join(changed_paths[:6]),
                    recommendation=(
                        "Ask whether existing tests cover the behavior, or add focused "
                        "regression tests for the changed paths."
                    ),
                )
            )

        for file in files:
            name = file.filename.rsplit("/", 1)[-1].lower()
            if name in DEPENDENCY_FILES:
                findings.append(
                    _finding(
                        title="Dependency manifest changed",
                        body=(
                            "Dependency changes can introduce licensing, supply-chain, "
                            "or runtime risk."
                        ),
                        severity=Severity.medium,
                        category=ReviewCategory.dependency,
                        confidence=0.78,
                        file_path=file.filename,
                        line=None,
                        evidence=f"+{file.additions}/-{file.deletions}",
                        recommendation=(
                            "Verify the new dependency versions, lockfile consistency, "
                            "and whether the change is covered by CI."
                        ),
                    )
                )

            if AUTH_PATH_RE.search(file.filename) and file.changes > 0:
                findings.append(
                    _finding(
                        title="Authentication or authorization code changed",
                        body=(
                            "Files related to auth, sessions, permissions, or roles "
                            "were modified."
                        ),
                        severity=Severity.high,
                        category=ReviewCategory.security,
                        confidence=0.74,
                        file_path=file.filename,
                        line=None,
                        evidence=f"{file.filename} +{file.additions}/-{file.deletions}",
                        recommendation=(
                            "Review privilege boundaries, negative-path tests, "
                            "token/session handling, and backward compatibility carefully."
                        ),
                    )
                )

            if MIGRATION_RE.search(file.filename):
                findings.append(
                    _finding(
                        title="Database migration or schema change",
                        body=(
                            "Database changes can affect deploy order, rollback, "
                            "and data compatibility."
                        ),
                        severity=Severity.medium,
                        category=ReviewCategory.reliability,
                        confidence=0.75,
                        file_path=file.filename,
                        line=None,
                        evidence=f"{file.filename} +{file.additions}/-{file.deletions}",
                        recommendation=(
                            "Check forward/backward compatibility, transaction safety, "
                            "and rollback strategy."
                        ),
                    )
                )

        for root, count in path_counter.items():
            if count >= 10:
                findings.append(
                    _finding(
                        title="Many files changed in one area",
                        body=f"{count} files changed under `{root}`.",
                        severity=Severity.low,
                        category=ReviewCategory.maintainability,
                        confidence=0.58,
                        file_path=root,
                        line=None,
                        evidence=f"{count} files",
                        recommendation=(
                            "Ask the author for a subsystem-level summary and targeted "
                            "review order."
                        ),
                    )
                )

        return findings

    def _dedupe(self, findings: list[ReviewFinding]) -> list[ReviewFinding]:
        seen: set[str] = set()
        unique: list[ReviewFinding] = []
        for finding in sorted(
            findings,
            key=lambda item: (
                ["critical", "high", "medium", "low", "info"].index(item.severity.value),
                -item.confidence,
            ),
        ):
            if finding.fingerprint in seen:
                continue
            seen.add(finding.fingerprint)
            unique.append(finding)
        return unique
