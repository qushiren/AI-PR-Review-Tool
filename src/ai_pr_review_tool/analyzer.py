from __future__ import annotations

from .context import ContextBuilder, ReviewContext
from .heuristics import HeuristicAnalyzer
from .llm import AIReviewer
from .schemas import (
    ChangedFile,
    PullRequestInfo,
    ReviewFinding,
    ReviewReport,
    ReviewSummary,
    Severity,
)

SEVERITY_ORDER = {
    Severity.critical: 0,
    Severity.high: 1,
    Severity.medium: 2,
    Severity.low: 3,
    Severity.info: 4,
}


class PullRequestAnalyzer:
    def __init__(self, max_patch_chars: int, ai_reviewer: AIReviewer | None = None) -> None:
        self.context_builder = ContextBuilder(max_patch_chars)
        self.heuristics = HeuristicAnalyzer()
        self.ai_reviewer = ai_reviewer

    async def analyze(
        self,
        pr: PullRequestInfo,
        files: list[ChangedFile],
        existing_comments: list[str],
    ) -> ReviewReport:
        context = self.context_builder.build(pr, files, existing_comments)
        findings = self.heuristics.analyze(files)
        model_used = None

        if self.ai_reviewer:
            ai_findings = await self.ai_reviewer.review(context)
            findings = self._merge_findings(findings, ai_findings)
            model_used = self.ai_reviewer.model

        return ReviewReport(
            pr=pr,
            summary=self._summarize(context, findings),
            findings=findings,
            existing_comment_count=len(existing_comments),
            model_used=model_used,
        )

    def _summarize(self, context: ReviewContext, findings: list[ReviewFinding]) -> ReviewSummary:
        risk_level = self._risk_level(findings, context.files)
        top_files = sorted(context.files, key=lambda file: file.changes, reverse=True)[:5]
        bullets = [
            f"{len(context.files)} files changed with +{context.additions}/-{context.deletions}.",
            "Largest changes: "
            + ", ".join(f"{file.filename} ({file.changes})" for file in top_files),
        ]
        if findings:
            high_signal = [
                finding
                for finding in findings
                if finding.severity in {Severity.critical, Severity.high, Severity.medium}
            ]
            bullets.append(f"{len(high_signal)} medium-or-higher review signals detected.")
        else:
            bullets.append("No deterministic high-risk patterns were detected.")

        return ReviewSummary(
            headline=f"{context.pr.title} appears to be a {risk_level.value} risk PR.",
            changed_files=len(context.files),
            additions=context.additions,
            deletions=context.deletions,
            risk_level=risk_level,
            bullets=bullets,
        )

    def _risk_level(self, findings: list[ReviewFinding], files: list[ChangedFile]) -> Severity:
        if any(finding.severity == Severity.critical for finding in findings):
            return Severity.critical
        if any(finding.severity == Severity.high for finding in findings):
            return Severity.high
        if any(finding.severity == Severity.medium for finding in findings):
            return Severity.medium
        if sum(file.changes for file in files) > 400:
            return Severity.medium
        return Severity.low if findings else Severity.info

    def _merge_findings(
        self, heuristic_findings: list[ReviewFinding], ai_findings: list[ReviewFinding]
    ) -> list[ReviewFinding]:
        merged: list[ReviewFinding] = []
        seen: set[tuple[str | None, int | None, str]] = set()
        for finding in [*heuristic_findings, *ai_findings]:
            key = (finding.file_path, finding.line, finding.title.lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append(finding)
        return sorted(merged, key=lambda item: (SEVERITY_ORDER[item.severity], -item.confidence))
