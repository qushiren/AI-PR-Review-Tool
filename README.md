# AI PR Review Tool

AI PR Review Tool helps developers review GitHub Pull Requests faster and more consistently. It fetches a PR, parses the changed files, summarizes intent, identifies risky code, and generates review suggestions that can be read locally or posted back to GitHub.

## What It Supports

- PR change summary grouped by file and risk area.
- Risk code detection for secrets, SQL injection patterns, auth-sensitive changes, broad exception handling, dangerous shell execution, dependency changes, generated files, and large diffs.
- Review suggestions with severity, confidence, affected file, affected line, evidence, and remediation.
- Optional OpenAI model analysis that receives a compact repository-aware context bundle.
- FastAPI service, browser UI, and CLI workflow.
- Optional posting of a Markdown review comment to the PR conversation.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

Set `GITHUB_TOKEN` in `.env`. `OPENAI_API_KEY` is optional; without it the tool runs the deterministic local analyzer.

Run the CLI:

```bash
ai-pr-review review https://github.com/owner/repo/pull/123
```

Run the Web API and UI:

```bash
uvicorn ai_pr_review_tool.api:app --reload
```

Open `http://127.0.0.1:8000`.

Post a PR comment:

```bash
ai-pr-review review https://github.com/owner/repo/pull/123 --post-comment
```

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `GITHUB_TOKEN` | Yes | GitHub token with read access to the repo. Add write access to post comments. |
| `OPENAI_API_KEY` | No | Enables model-assisted review. |
| `OPENAI_MODEL` | No | Defaults to `gpt-4.1-mini`. |
| `AI_REVIEW_MAX_PATCH_CHARS` | No | Maximum patch budget sent into analysis. |

## Design Notes

See [docs/DESIGN.md](docs/DESIGN.md) for model choice, context gathering, false-positive control, speed decisions, and extension roadmap.

## Development

```bash
pytest
ruff check .
```
