import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class Desired(BaseModel):
    roles: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    remote_ok: bool = True
    salary_min: int | None = None
    salary_max: int | None = None
    keywords_exclude: list[str] = Field(default_factory=list)


class Profile(BaseModel):
    name: str
    skills: list[str] = Field(default_factory=list)
    years: float = 0.0
    education: str = ""
    resume_md: str
    resume_version: str = ""
    desired: Desired = Field(default_factory=Desired)

    @model_validator(mode="after")
    def _ensure_resume_version(self) -> "Profile":
        if not self.resume_version:
            self.resume_version = hashlib.sha1(self.resume_md.encode("utf-8")).hexdigest()[:12]
        return self


def load_profile(path: Path | str) -> Profile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Profile.model_validate(data)
