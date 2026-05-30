from __future__ import annotations

from .analyzer import PullRequestAnalyzer
from .comment_renderer import render_markdown_report
from .config import Settings
from .github_client import GitHubClient, parse_pr_url
from .llm import AIReviewer
from .schemas import ReviewReport


class ReviewService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def review_pr(
        self,
        pr_url: str,
        *,
        use_ai: bool = True,
        post_comment: bool = False,
    ) -> tuple[ReviewReport, str | None]:
        ref = parse_pr_url(pr_url)
        ai_reviewer = None
        if use_ai and self.settings.openai_api_key:
            ai_reviewer = AIReviewer(self.settings.openai_api_key, self.settings.openai_model)

        async with GitHubClient(
            token=self.settings.github_token,
            timeout_seconds=self.settings.request_timeout_seconds,
        ) as github:
            pr = await github.fetch_pr(ref)
            files = await github.fetch_files(ref)
            comments = await github.fetch_issue_comments(ref)

            analyzer = PullRequestAnalyzer(
                max_patch_chars=self.settings.max_patch_chars,
                ai_reviewer=ai_reviewer,
            )
            report = await analyzer.analyze(pr, files, comments)
            comment_url = None
            if post_comment:
                comment_url = await github.post_issue_comment(ref, render_markdown_report(report))
            return report, comment_url
