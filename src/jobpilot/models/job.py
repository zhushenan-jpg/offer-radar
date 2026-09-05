import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


class JobPosting(BaseModel):
    id: str = Field(min_length=16, max_length=16)
    source: Literal["greenhouse", "lever", "manual"]
    company: str
    title: str
    location: str = ""
    remote: bool = False
    url: str = ""
    department: str = ""
    description_md: str
    fingerprint: str = ""
    first_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["new", "parsed", "scored", "review", "error", "archived"] = "new"

    @classmethod
    def compute_id(cls, source: str, company: str, title: str, location: str) -> str:
        """归一化后哈希,大小写与多余空白不影响身份."""
        raw = "|".join([source, _norm(company), _norm(title), _norm(location)])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def model_post_init(self, __context, /) -> None:
        if not self.fingerprint:
            self.fingerprint = self.id
