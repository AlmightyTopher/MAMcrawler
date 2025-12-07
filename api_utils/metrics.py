"""
Metrics Collector

Collects performance and usage metrics for API clients.

Author: Agent 10 - API Client Consolidation Specialist
"""

class MetricsCollector:
    """Simple metrics collector placeholder."""

    def __init__(self):
        self.data = {}

    def collect(self, name: str, value):
        """Collect a metric."""
        self.data[name] = value

    def get_metrics(self):
        """Get collected metrics."""
        return self.data