from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class ReviewCategory(str, Enum):
    security = "security"
    correctness = "correctness"
    reliability = "reliability"
    maintainability = "maintainability"
    performance = "performance"
    testing = "testing"
    documentation = "documentation"
    dependency = "dependency"


class PRReference(BaseModel):
    owner: str
    repo: str
    number: int

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


class PullRequestInfo(BaseModel):
    ref: PRReference
    title: str
    body: str | None = None
    author: str | None = None
    url: HttpUrl | str
    base_branch: str
    head_branch: str


class ChangedFile(BaseModel):
    filename: str
    status: str
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None
    raw_url: str | None = None
    contents_url: str | None = None


class HunkLine(BaseModel):
    filename: str
    line_no: int | None
    old_line_no: int | None = None
    kind: str
    text: str
    hunk_header: str


class ReviewFinding(BaseModel):
    title: str
    body: str
    severity: Severity
    category: ReviewCategory
    confidence: float = Field(ge=0, le=1)
    file_path: str | None = None
    line: int | None = None
    evidence: str | None = None
    recommendation: str
    source: str = "heuristic"
    fingerprint: str


class ReviewSummary(BaseModel):
    headline: str
    changed_files: int
    additions: int
    deletions: int
    risk_level: Severity
    bullets: list[str]


class ReviewReport(BaseModel):
    pr: PullRequestInfo
    summary: ReviewSummary
    findings: list[ReviewFinding]
    existing_comment_count: int = 0
    model_used: str | None = None


class ReviewRequest(BaseModel):
    pr_url: str
    use_ai: bool = True
    post_comment: bool = False
