"""数据采集层:Greenhouse/Lever 官方公开 API,零爬虫."""

from .base import Collector, CollectorError
from .greenhouse import GreenhouseCollector
from .lever import LeverCollector

_REGISTRY = {"greenhouse": GreenhouseCollector, "lever": LeverCollector}


def get_collector(source: str, client) -> Collector:
    try:
        return _REGISTRY[source](client)
    except KeyError:
        raise CollectorError(f"未知数据源类型: {source}") from None


__all__ = ["Collector", "CollectorError", "GreenhouseCollector", "LeverCollector", "get_collector"]
