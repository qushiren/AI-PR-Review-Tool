from __future__ import annotations

from dataclasses import dataclass

from .diff_parser import truncate_patch
from .schemas import ChangedFile, PullRequestInfo


@dataclass(frozen=True)
class ReviewContext:
    pr: PullRequestInfo
    files: list[ChangedFile]
    existing_comments: list[str]
    patch_bundle: str

    @property
    def additions(self) -> int:
        return sum(file.additions for file in self.files)

    @property
    def deletions(self) -> int:
        return sum(file.deletions for file in self.files)


class ContextBuilder:
    def __init__(self, max_patch_chars: int) -> None:
        self.max_patch_chars = max_patch_chars

    def build(
        self,
        pr: PullRequestInfo,
        files: list[ChangedFile],
        existing_comments: list[str],
    ) -> ReviewContext:
        return ReviewContext(
            pr=pr,
            files=files,
            existing_comments=existing_comments[-30:],
            patch_bundle=truncate_patch(files, self.max_patch_chars),
        )
