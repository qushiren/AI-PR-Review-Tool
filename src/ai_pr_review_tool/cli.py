from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from .comment_renderer import render_markdown_report
from .config import get_settings
from .service import ReviewService

app = typer.Typer(help="AI-assisted GitHub Pull Request review tool.")
console = Console()


@app.command()
def review(
    pr_url: str = typer.Argument(
        ..., help="GitHub PR URL, for example https://github.com/a/b/pull/1"
    ),
    use_ai: bool = typer.Option(
        True, "--ai/--no-ai", help="Use OpenAI when OPENAI_API_KEY is set."
    ),
    post_comment: bool = typer.Option(
        False, help="Post the rendered report to the PR conversation."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Print structured JSON instead of Markdown."
    ),
) -> None:
    """Fetch, analyze, and optionally comment on a Pull Request."""
    asyncio.run(
        _review(pr_url, use_ai=use_ai, post_comment=post_comment, json_output=json_output)
    )


async def _review(pr_url: str, *, use_ai: bool, post_comment: bool, json_output: bool) -> None:
    service = ReviewService(get_settings())
    report, comment_url = await service.review_pr(
        pr_url, use_ai=use_ai, post_comment=post_comment
    )

    if json_output:
        console.print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    else:
        console.print(Markdown(render_markdown_report(report)))
        if comment_url:
            console.print(f"\nPosted PR comment: {comment_url}")


@app.command()
def config() -> None:
    """Show effective non-secret configuration."""
    settings = get_settings()
    table = Table(title="AI PR Review Tool Configuration")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("GitHub token", "configured" if settings.github_token else "missing")
    table.add_row("OpenAI key", "configured" if settings.openai_api_key else "missing")
    table.add_row("OpenAI model", settings.openai_model)
    table.add_row("Patch budget", str(settings.max_patch_chars))
    console.print(table)


if __name__ == "__main__":
    app()
