from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from .context import ReviewContext
from .schemas import ReviewCategory, ReviewFinding, Severity

SYSTEM_PROMPT = """You are a senior code reviewer.
Return only JSON with a top-level "findings" array.
Each finding must include title, body, severity, category, confidence, file_path, line,
evidence, and recommendation.
Prefer high-confidence correctness, security, reliability, and testing issues.
Avoid style-only comments and avoid repeating existing PR discussion.
"""


class AIReviewer:
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def review(self, context: ReviewContext) -> list[ReviewFinding]:
        user_prompt = self._build_prompt(context)
        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_findings(content)

    def _build_prompt(self, context: ReviewContext) -> str:
        comments = "\n\n".join(context.existing_comments[-10:]) or "No existing comments."
        return f"""
PR: {context.pr.title}
URL: {context.pr.url}
Author: {context.pr.author}
Base: {context.pr.base_branch}
Head: {context.pr.head_branch}

Existing review discussion:
{comments}

Changed files and patches:
{context.patch_bundle}
"""

    def _parse_findings(self, content: str) -> list[ReviewFinding]:
        try:
            payload: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            return []

        findings: list[ReviewFinding] = []
        for index, raw in enumerate(payload.get("findings", [])):
            if not isinstance(raw, dict):
                continue
            try:
                file_path = raw.get("file_path")
                line = raw.get("line")
                evidence = raw.get("evidence")
                finding = ReviewFinding(
                    title=str(raw.get("title") or "AI review finding"),
                    body=str(raw.get("body") or ""),
                    severity=Severity(str(raw.get("severity") or "medium").lower()),
                    category=ReviewCategory(str(raw.get("category") or "maintainability").lower()),
                    confidence=float(raw.get("confidence") or 0.5),
                    file_path=str(file_path) if file_path else None,
                    line=int(line) if line else None,
                    evidence=str(evidence) if evidence else None,
                    recommendation=str(raw.get("recommendation") or "Review this change manually."),
                    source="openai",
                    fingerprint=f"openai-{index}-{hash(str(raw))}",
                )
            except (ValueError, ValidationError):
                continue
            findings.append(finding)
        return findings
