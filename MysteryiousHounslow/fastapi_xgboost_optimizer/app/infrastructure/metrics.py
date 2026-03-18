from typing import Dict, Any
import time
from dataclasses import dataclass, field


@dataclass
class Counter:
    """Simple counter metric."""

    _value: float = 0.0

    def inc(self, amount: float = 1.0):
        self._value += amount

    def get(self) -> float:
        return self._value


@dataclass
class Gauge:
    """Simple gauge metric."""

    _value: float = 0.0

    def set(self, value: float):
        self._value = value

    def get(self) -> float:
        return self._value


@dataclass
class Histogram:
    """Simple histogram metric."""

    _values: list = field(default_factory=list)
    _sum: float = 0.0
    _count: int = 0

    def observe(self, value: float):
        self._values.append(value)
        self._sum += value
        self._count += 1

    def get(self) -> Dict[str, float]:
        if not self._values:
            return {"sum": 0.0, "count": 0, "avg": 0.0}
        return {"sum": self._sum, "count": self._count, "avg": self._sum / self._count}


class Metrics:
    """Application metrics collection."""

    def __init__(self):
        # Request metrics
        self.requests_total = Counter()
        self.requests_duration = Histogram()

        # Optimization metrics
        self.optimization_success_rate = Gauge()
        self.active_optimizations = Gauge()
        self.optimization_duration = Histogram()

        # System metrics
        self.memory_usage = Gauge()
        self.cpu_usage = Gauge()

    def record_request(self, duration: float, status_code: int):
        """Record HTTP request metrics."""
        self.requests_total.inc()
        self.requests_duration.observe(duration)

    def record_optimization_start(self):
        """Record optimization start."""
        self.active_optimizations.set(self.active_optimizations.get() + 1)

    def record_optimization_end(self, success: bool, duration: float):
        """Record optimization completion."""
        self.active_optimizations.set(max(0, self.active_optimizations.get() - 1))
        self.optimization_duration.observe(duration)
        self.optimization_success_rate.set(1.0 if success else 0.0)


# Global metrics instance
metrics = Metrics()
