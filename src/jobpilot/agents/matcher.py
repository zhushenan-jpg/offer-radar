"""Matcher:简历 × JD → MatchScore(带证据链),缓存 key 绑定全部版本号."""

from jobpilot.llm_gateway.gateway import make_cache_key
from jobpilot.models.profile import Profile
from jobpilot.models.score import MatchScore

from .prompts import RUBRIC_VERSION, SYSTEM_MATCHER, build_matcher_prompt


def score_job(gateway, profile: Profile, jd_md: str, *, job_id: str) -> tuple[MatchScore, str]:
    """返回 (评分, cache_key)。任何影响结果的因素都必须进 cache_key."""
    key = make_cache_key(RUBRIC_VERSION, profile.resume_version, job_id, gateway.cfg.model)
    score = gateway.json_in(
        MatchScore,
        build_matcher_prompt(profile, jd_md),
        system=SYSTEM_MATCHER,
        cache_key=key,
        module="matcher",
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
