"""Matcher:简历 × JD → MatchScore(带证据链),缓存 key 绑定全部版本号."""

import re

from jobpilot.llm_gateway.gateway import make_cache_key
from jobpilot.models.profile import Profile
from jobpilot.models.score import DIMS, MatchScore

from .prompts import RUBRIC_VERSION, SYSTEM_MATCHER, build_matcher_prompt

_PUNCT_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff]+")
_URL_RE = re.compile(r"https?://\S+")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def canonical_text(text: str) -> str:
    """引号/破折号/链接等排版变体统一后,只保留字母数字汉字。

    HTML 来源的 JD 带弯引号(')与 markdown 链接语法,模型引用的是
    渲染后的可读文本;比对必须忽略 URL、标点与空白差异,但仍能抓住
    改词级的幻觉。顺序敏感:必须先还原 markdown 链接(此时括号尚
    完整),再剥裸 URL,否则孤立的 '[' 会让链接正则吞掉大段正文。
    """
    text = text.lower()
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    text = (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    return _PUNCT_RE.sub("", text)


def evidence_validator(jd_md: str):
    """反幻觉硬门:所有证据引用必须是 JD 的逐字内容(标点变体容忍),否则回喂重评."""
    canonical_jd = canonical_text(jd_md)

    def _check(score: MatchScore) -> list[str]:
        bad = []
        for dim in DIMS:
            for ev in score.dims[dim].evidence:
                if canonical_text(ev.quote) not in canonical_jd:
                    bad.append(f"{dim}:「{ev.quote}」")
        return bad

    return _check


def score_job(gateway, profile: Profile, jd_md: str, *, job_id: str) -> tuple[MatchScore, str]:
    """返回 (评分, cache_key)。任何影响结果的因素都必须进 cache_key."""
    key = make_cache_key(RUBRIC_VERSION, profile.resume_version, job_id, gateway.cfg.model)
    score = gateway.json_in(
        MatchScore,
        build_matcher_prompt(profile, jd_md),
        system=SYSTEM_MATCHER,
        cache_key=key,
        module="matcher",
        validator=evidence_validator(jd_md),
    )
    return score, key


def score_and_store(gateway, storage, profile: Profile, jd_md: str, *, job_id: str) -> MatchScore:
    score, _ = score_job(gateway, profile, jd_md, job_id=job_id)
    storage.scores.save(
        job_id,
        score,
        rubric_version=RUBRIC_VERSION,
        model_version=gateway.cfg.model,
        resume_version=profile.resume_version,
    )
    return score
