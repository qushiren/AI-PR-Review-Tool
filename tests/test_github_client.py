import pytest

from ai_pr_review_tool.github_client import parse_pr_url


def test_parse_pr_url() -> None:
    ref = parse_pr_url("https://github.com/example/project/pull/42")

    assert ref.owner == "example"
    assert ref.repo == "project"
    assert ref.number == 42
    assert ref.full_name == "example/project"


def test_parse_pr_url_rejects_issue_url() -> None:
    with pytest.raises(ValueError):
        parse_pr_url("https://github.com/example/project/issues/42")
