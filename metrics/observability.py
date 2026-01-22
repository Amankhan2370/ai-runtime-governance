"""
Observability and metrics collection for control plane.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Observability:
    """
    Metrics and observability for control plane.
    """
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_blocked": 0,
            "requests_retried": 0,
            "requests_downgraded": 0,
            "cost_total": 0.0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0
        }
    
    def record_request(
        self,
        action: str,
        cost: float,
        latency_ms: float
    ):
        """Record request metrics."""
        self.metrics["requests_total"] += 1
        
        if action == "block":
            self.metrics["requests_blocked"] += 1
        elif action == "retry":
            self.metrics["requests_retried"] += 1
        elif action == "downgrade":
            self.metrics["requests_downgraded"] += 1
        
        self.metrics["cost_total"] += cost
        # Simplified latency tracking
        self.metrics["latency_p50"] = latency_ms
        self.metrics["latency_p95"] = latency_ms * 1.5
        self.metrics["latency_p99"] = latency_ms * 2.0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()
