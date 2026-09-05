"""数据采集层:Greenhouse/Lever 官方 API 为主,browser-use 兜底(可选依赖)."""

from .base import Collector, CollectorError
from .browser import BrowserCollector
from .greenhouse import GreenhouseCollector
from .lever import LeverCollector

_REGISTRY = {
    "greenhouse": GreenhouseCollector,
    "lever": LeverCollector,
    "browser": BrowserCollector,
}


def get_collector(source: str, client, cfg=None) -> Collector:
    try:
        cls = _REGISTRY[source]
    except KeyError:
        raise CollectorError(f"未知数据源类型: {source}") from None
    if cls is BrowserCollector:
        return cls(client, cfg=cfg)
    return cls(client)


__all__ = [
    "BrowserCollector",
    "Collector",
    "CollectorError",
    "GreenhouseCollector",
    "LeverCollector",
    "get_collector",
]
