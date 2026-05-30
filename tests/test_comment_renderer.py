from ai_pr_review_tool.comment_renderer import render_markdown_report
from ai_pr_review_tool.schemas import (
    PRReference,
    PullRequestInfo,
    ReviewCategory,
    ReviewFinding,
    ReviewReport,
    ReviewSummary,
    Severity,
)


def test_render_markdown_report_includes_findings() -> None:
    report = ReviewReport(
        pr=PullRequestInfo(
            ref=PRReference(owner="example", repo="project", number=1),
            title="Improve auth",
            body=None,
            author="dev",
            url="https://github.com/example/project/pull/1",
            base_branch="main",
            head_branch="feature",
        ),
        summary=ReviewSummary(
            headline="Improve auth appears to be a high risk PR.",
            changed_files=1,
            additions=10,
            deletions=2,
            risk_level=Severity.high,
            bullets=["1 file changed."],
        ),
        findings=[
            ReviewFinding(
                title="Authentication or authorization code changed",
                body="Auth code was modified.",
                severity=Severity.high,
                category=ReviewCategory.security,
                confidence=0.74,
                file_path="auth.py",
                line=None,
                evidence="auth.py +10/-2",
                recommendation="Review privilege boundaries.",
                fingerprint="abc",
            )
        ],
    )

    markdown = render_markdown_report(report)

    assert "AI PR Review" in markdown
    assert "Authentication or authorization code changed" in markdown
    assert "auth.py" in markdown
