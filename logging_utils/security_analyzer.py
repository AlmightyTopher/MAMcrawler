"""
Security analysis utilities for the unified logging system.

Provides tools for analyzing security events and detecting potential threats.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from logging_system import get_logger, log_security_event


class SecurityAnalyzer:
    """Analyze security events in logs"""

    def __init__(self):
        self.logger = get_logger("security_analyzer")
        self.suspicious_patterns = [
            r'failed.*login',
            r'unauthorized.*access',
            r'sql.*injection',
            r'cross.*site',
            r'xss',
            r'brute.*force',
            r'suspicious.*activity',
            r'malware',
            r'exploit'
        ]

    def analyze_security_events(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze logs for security events"""
        security_events = []
        threat_indicators = Counter()
        ip_addresses = Counter()
        user_agents = Counter()

        for log in logs:
            if self._is_security_event(log):
                security_events.append(log)

                # Extract threat indicators
                message = log.get('message', '').lower()
                for pattern in self.suspicious_patterns:
                    if pattern.replace('.*', ' ').replace('*', ' ') in message:
                        threat_indicators[pattern] += 1

                # Extract IP addresses (simple pattern)
                import re
                ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', str(log))
                for ip in ips:
                    ip_addresses[ip] += 1

        return {
            'total_security_events': len(security_events),
            'threat_indicators': dict(threat_indicators.most_common(10)),
            'suspicious_ips': dict(ip_addresses.most_common(10)),
            'events': security_events[-50:]  # Last 50 events
        }

    def _is_security_event(self, log: Dict[str, Any]) -> bool:
        """Check if log entry is a security event"""
        level = log.get('level', '').upper()
        if level in ['SECURITY', 'CRITICAL']:
            return True

        message = log.get('message', '').lower()
        security_keywords = [
            'security', 'auth', 'login', 'access', 'permission',
            'unauthorized', 'suspicious', 'threat', 'attack', 'breach'
        ]

        return any(keyword in message for keyword in security_keywords)

    def detect_anomalies(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalous patterns in logs"""
        anomalies = []

        # Simple anomaly detection based on frequency
        recent_logs = logs[-1000:]  # Last 1000 logs
        error_rate = sum(1 for log in recent_logs if log.get('level') == 'ERROR') / len(recent_logs)

        if error_rate > 0.1:  # More than 10% errors
            anomalies.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'description': f'High error rate detected: {error_rate:.1%}',
                'recommendation': 'Investigate recent errors and system health'
            })

        # Check for rapid repeated failures from same source
        failure_counts = Counter()
        for log in recent_logs:
            if log.get('level') in ['ERROR', 'CRITICAL']:
                # Use logger name as source identifier
                source = log.get('logger', 'unknown')
                failure_counts[source] += 1

        for source, count in failure_counts.items():
            if count > 10:  # More than 10 failures from same source
                anomalies.append({
                    'type': 'repeated_failures',
                    'severity': 'medium',
                    'description': f'Repeated failures from {source}: {count} times',
                    'recommendation': 'Check system component health'
                })

        return anomalies