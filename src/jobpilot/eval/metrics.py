"""评测指标:模型评分 vs 人工标注的一致性。全部纯函数,便于 TDD."""

from scipy.stats import spearmanr


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman 等级相关;样本 <3 或任一侧为常数时无意义,返回 None."""
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    corr, _ = spearmanr(xs, ys)
    return round(float(corr), 3)


def mae(xs: list[float], ys: list[float]) -> float | None:
    if not xs or len(xs) != len(ys):
        return None
    return round(sum(abs(x - y) for x, y in zip(xs, ys)) / len(xs), 1)


def topk_overlap(
    pred: list[tuple[str, float]], human: list[tuple[str, float]], k: int = 3
) -> float | None:
    """双方 Top-k 职位集合的重合率(0-1);任一侧不足 k 条时无意义."""
    if len(pred) < k or len(human) < k:
        return None
    p = {jid for jid, _ in sorted(pred, key=lambda t: -t[1])[:k]}
    h = {jid for jid, _ in sorted(human, key=lambda t: -t[1])[:k]}
    return round(len(p & h) / k, 2)


def calibration(pairs: list[tuple[float, float]], n_bins: int = 4) -> list[dict]:
    """按模型分位桶,看每桶内人工分的均值——观察系统性高估/低估."""
    if not pairs:
        return []
    width = 100 / n_bins
    out = []
    for b in range(n_bins):
        lo, hi = b * width, (b + 1) * width
        bucket = [h for p, h in pairs if lo <= p < hi or (b == n_bins - 1 and p == 100)]
        out.append(
            {
                "range": f"{lo:.0f}-{hi:.0f}",
                "n": len(bucket),
                "mean_pred": round(
                    sum(p for p, h in pairs if lo <= p < hi or (b == n_bins - 1 and p == 100))
                    / len(bucket),
                    1,
                )
                if bucket
                else None,
                "mean_human": round(sum(bucket) / len(bucket), 1) if bucket else None,
            }
        )
    return out


def compute_metrics(pairs: list[dict], top_k: int = 3) -> dict:
    """pairs: [{job_id, title, pred, human}] → 全部指标."""
    xs = [p["pred"] for p in pairs]
    ys = [p["human"] for p in pairs]
    return {
        "n": len(pairs),
        "spearman": spearman(xs, ys),
        "mae": mae(xs, ys),
        "topk_overlap": topk_overlap(
            [(p["job_id"], p["pred"]) for p in pairs],
            [(p["job_id"], p["human"]) for p in pairs],
            k=top_k,
        ),
        "calibration": calibration(list(zip(xs, ys))),
        "pairs": pairs,
    }
