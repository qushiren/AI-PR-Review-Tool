from ai_pr_review_tool.heuristics import HeuristicAnalyzer
from ai_pr_review_tool.schemas import ChangedFile, Severity


def test_detects_secret_in_added_line() -> None:
    findings = HeuristicAnalyzer().analyze(
        [
            ChangedFile(
                filename="settings.py",
                status="modified",
                additions=1,
                deletions=0,
                changes=1,
                patch='@@ -1,0 +1,1 @@\n+API_KEY = "abcdef1234567890"\n',
            )
        ]
    )

    assert findings
    assert findings[0].severity == Severity.critical
    assert findings[0].file_path == "settings.py"


def test_dependency_manifest_change_is_flagged() -> None:
    findings = HeuristicAnalyzer().analyze(
        [
            ChangedFile(
                filename="pyproject.toml",
                status="modified",
                additions=5,
                deletions=1,
                changes=6,
                patch="@@ -1 +1 @@\n+fastapi = '*'\n",
            )
        ]
    )

    assert any(finding.title == "Dependency manifest changed" for finding in findings)
