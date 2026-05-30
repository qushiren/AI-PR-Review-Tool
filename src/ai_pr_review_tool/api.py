from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .comment_renderer import render_markdown_report
from .config import get_settings
from .github_client import GitHubError
from .schemas import ReviewRequest
from .service import ReviewService

app = FastAPI(
    title="AI PR Review Tool",
    description="Fetch and analyze GitHub Pull Requests with deterministic and AI-assisted review.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory="src/ai_pr_review_tool/static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("src/ai_pr_review_tool/static/index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reviews")
async def create_review(request: ReviewRequest) -> dict[str, object]:
    service = ReviewService(get_settings())
    try:
        report, comment_url = await service.review_pr(
            request.pr_url,
            use_ai=request.use_ai,
            post_comment=request.post_comment,
        )
    except (GitHubError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"report": report.model_dump(mode="json"), "comment_url": comment_url}


@app.post("/reviews/markdown", response_class=PlainTextResponse)
async def create_review_markdown(request: ReviewRequest) -> str:
    service = ReviewService(get_settings())
    try:
        report, _ = await service.review_pr(
            request.pr_url,
            use_ai=request.use_ai,
            post_comment=False,
        )
    except (GitHubError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return render_markdown_report(report)
