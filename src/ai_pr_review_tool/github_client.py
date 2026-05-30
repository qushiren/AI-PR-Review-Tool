from __future__ import annotations

import re
from typing import Any

import httpx

from .schemas import ChangedFile, PRReference, PullRequestInfo

PR_URL_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


class GitHubError(RuntimeError):
    pass


def parse_pr_url(pr_url: str) -> PRReference:
    match = PR_URL_RE.fullmatch(pr_url.strip().rstrip("/"))
    if not match:
        raise ValueError("Expected a GitHub PR URL like https://github.com/owner/repo/pull/123")
    return PRReference(
        owner=match.group("owner"),
        repo=match.group("repo"),
        number=int(match.group("number")),
    )


class GitHubClient:
    def __init__(self, token: str | None, timeout_seconds: float = 20) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-pr-review-tool",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=timeout_seconds,
        )

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_pr(self, ref: PRReference) -> PullRequestInfo:
        data = await self._get(f"/repos/{ref.full_name}/pulls/{ref.number}")
        return PullRequestInfo(
            ref=ref,
            title=data["title"],
            body=data.get("body"),
            author=(data.get("user") or {}).get("login"),
            url=data["html_url"],
            base_branch=data["base"]["ref"],
            head_branch=data["head"]["ref"],
        )

    async def fetch_files(self, ref: PRReference) -> list[ChangedFile]:
        items: list[dict[str, Any]] = await self._get_paginated(
            f"/repos/{ref.full_name}/pulls/{ref.number}/files"
        )
        return [
            ChangedFile(
                filename=item["filename"],
                status=item["status"],
                additions=item.get("additions", 0),
                deletions=item.get("deletions", 0),
                changes=item.get("changes", 0),
                patch=item.get("patch"),
                raw_url=item.get("raw_url"),
                contents_url=item.get("contents_url"),
            )
            for item in items
        ]

    async def fetch_issue_comments(self, ref: PRReference) -> list[str]:
        items: list[dict[str, Any]] = await self._get_paginated(
            f"/repos/{ref.full_name}/issues/{ref.number}/comments"
        )
        return [item.get("body", "") for item in items if item.get("body")]

    async def post_issue_comment(self, ref: PRReference, body: str) -> str:
        data = await self._post(
            f"/repos/{ref.full_name}/issues/{ref.number}/comments", {"body": body}
        )
        return data["html_url"]

    async def _get(self, path: str) -> Any:
        response = await self._client.get(path)
        return self._handle(response)

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        response = await self._client.post(path, json=payload)
        return self._handle(response)

    async def _get_paginated(self, path: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            response = await self._client.get(path, params={"per_page": 100, "page": page})
            data = self._handle(response)
            if not data:
                return results
            results.extend(data)
            if "next" not in response.links:
                return results
            page += 1

    def _handle(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("message", detail)
            except ValueError:
                pass
            raise GitHubError(f"GitHub API {response.status_code}: {detail}")
        return response.json()
