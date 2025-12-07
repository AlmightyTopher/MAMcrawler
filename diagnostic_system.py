#!/usr/bin/env python3
"""
Unified Diagnostic System for MAMcrawler
Consolidated diagnostic and monitoring framework
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Import diagnostic modules
from diagnostic_modules import (
    ABSDiagnostic,
    QBittorrentDiagnostic,
    VPNDiagnostic,
    MAMDiagnostic,
    ProwlarrDiagnostic,
    WorkflowDiagnostic,
    SystemDiagnostic
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    handlers=[
        logging.FileHandler('diagnostic.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DiagnosticSystem:
    """Main diagnostic system controller"""

    def __init__(self):
        self.modules = {
            'abs': ABSDiagnostic(),
            'qbittorrent': QBittorrentDiagnostic(),
            'vpn': VPNDiagnostic(),
            'mam': MAMDiagnostic(),
            'prowlarr': ProwlarrDiagnostic(),
            'workflow': WorkflowDiagnostic(),
            'system': SystemDiagnostic()
        }
        self.reports_dir = Path('diagnostic_reports')
        self.reports_dir.mkdir(exist_ok=True)

    def run_health_check(self, modules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comprehensive health check"""
        logger.info("Starting comprehensive health check...")

        if modules is None:
            modules = list(self.modules.keys())

        results = {}
        for module_name in modules:
            if module_name in self.modules:
                logger.info(f"Running {module_name} diagnostics...")
                try:
                    results[module_name] = self.modules[module_name].run()
                except Exception as e:
                    logger.error(f"Error running {module_name} diagnostics: {e}")
                    results[module_name] = {
                        "module": module_name,
                        "error": str(e),
                        "overall_status": "ERROR",
                        "timestamp": datetime.now().isoformat()
                    }

        # Generate summary
        summary = self._generate_summary(results)
        results['_summary'] = summary

        logger.info(f"Health check complete. Overall status: {summary['overall_status']}")
        return results

    def run_single_module(self, module_name: str) -> Dict[str, Any]:
        """Run diagnostics for a single module"""
        if module_name not in self.modules:
            available = ', '.join(self.modules.keys())
            raise ValueError(f"Unknown module '{module_name}'. Available: {available}")

        logger.info(f"Running {module_name} diagnostics...")
        result = self.modules[module_name].run()
        logger.info(f"{module_name} diagnostics complete: {result['overall_status']}")
        return result

    def run_monitoring(self, interval: int = 300, duration: int = 3600):
        """Run continuous monitoring"""
        import time
        import asyncio

        logger.info(f"Starting continuous monitoring (interval: {interval}s, duration: {duration}s)")

        end_time = time.time() + duration
        check_count = 0

        while time.time() < end_time:
            check_count += 1
            logger.info(f"=== MONITORING CHECK #{check_count} ===")

            try:
                results = self.run_health_check()
                self.save_report(results, f"monitoring_{check_count}_{int(time.time())}")

                # Log summary
                summary = results.get('_summary', {})
                logger.info(f"Check {check_count}: {summary.get('overall_status')} "
                          f"({summary.get('total_checks')} checks, "
                          f"{summary.get('errors')} errors, "
                          f"{summary.get('warnings')} warnings)")

            except Exception as e:
                logger.error(f"Monitoring check {check_count} failed: {e}")

            if time.time() + interval < end_time:
                logger.info(f"Next check in {interval} seconds...")
                time.sleep(interval)

        logger.info("Continuous monitoring complete")

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall summary from results"""
        total_checks = 0
        ok_count = 0
        warning_count = 0
        error_count = 0
        critical_count = 0

        module_summaries = {}

        for module_name, result in results.items():
            if module_name.startswith('_'):
                continue

            module_summaries[module_name] = result
            total_checks += result.get('total_checks', 0)
            ok_count += result.get('ok', 0)
            warning_count += result.get('warnings', 0)
            error_count += result.get('errors', 0)
            critical_count += result.get('critical', 0)

        # Determine overall status
        if critical_count > 0:
            overall_status = "CRITICAL"
        elif error_count > 0:
            overall_status = "ERROR"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "OK"

        success_rate = (ok_count / total_checks * 100) if total_checks > 0 else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "total_checks": total_checks,
            "ok": ok_count,
            "warnings": warning_count,
            "errors": error_count,
            "critical": critical_count,
            "success_rate": round(success_rate, 1),
            "modules_checked": len([k for k in results.keys() if not k.startswith('_')]),
            "module_summaries": module_summaries
        }

    def save_report(self, results: Dict[str, Any], filename: Optional[str] = None,
                   format: str = 'json') -> str:
        """Save diagnostic report"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"diagnostic_report_{timestamp}"

        if format == 'json':
            filepath = self.reports_dir / f"{filename}.json"
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        elif format == 'html':
            filepath = self.reports_dir / f"{filename}.html"
            html_content = self._generate_html_report(results)
            with open(filepath, 'w') as f:
                f.write(html_content)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Report saved: {filepath}")
        return str(filepath)

    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """Generate HTML report"""
        summary = results.get('_summary', {})

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MAMcrawler Diagnostic Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #e8f4f8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .module {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .status-ok {{ background: #d4edda; border-color: #c3e6cb; }}
        .status-warning {{ background: #fff3cd; border-color: #ffeaa7; }}
        .status-error {{ background: #f8d7da; border-color: #f5c6cb; }}
        .status-critical {{ background: #f8d7da; border-color: #f5c6cb; }}
        .result {{ margin: 5px 0; padding: 5px; background: #f9f9f9; border-radius: 3px; }}
        .recommendations {{ background: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>MAMcrawler Diagnostic Report</h1>
        <p>Generated: {summary.get('timestamp', 'Unknown')}</p>
        <p>Overall Status: <strong>{summary.get('overall_status', 'Unknown')}</strong></p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <p>Total Checks: {summary.get('total_checks', 0)}</p>
        <p>Success Rate: {summary.get('success_rate', 0)}%</p>
        <p>OK: {summary.get('ok', 0)} | Warnings: {summary.get('warnings', 0)} | Errors: {summary.get('errors', 0)} | Critical: {summary.get('critical', 0)}</p>
    </div>
"""

        # Add module details
        for module_name, module_result in summary.get('module_summaries', {}).items():
            status_class = f"status-{module_result.get('overall_status', 'unknown').lower()}"
            html += f"""
    <div class="module {status_class}">
        <h3>{module_name.upper()} - {module_result.get('overall_status', 'Unknown')}</h3>
        <p>{module_result.get('description', '')}</p>
"""

            # Add detailed results
            if 'results' in results.get(module_name, {}):
                for result in results[module_name]['results']:
                    html += f"""
        <div class="result">
            <strong>{result['component']}:</strong> {result['message']}
            {f"<br><em>Recommendations: {', '.join(result.get('recommendations', []))}</em>" if result.get('recommendations') else ""}
        </div>
"""

            html += "    </div>"

        html += """
</body>
</html>
"""
        return html

    def print_summary(self, results: Dict[str, Any]):
        """Print human-readable summary"""
        summary = results.get('_summary', {})

        print("\n" + "="*80)
        print("MAMCRAWLER DIAGNOSTIC SUMMARY")
        print("="*80)
        print(f"Timestamp: {summary.get('timestamp', 'Unknown')}")
        print(f"Overall Status: {summary.get('overall_status', 'Unknown')}")
        print(f"Modules Checked: {summary.get('modules_checked', 0)}")
        print(f"Total Checks: {summary.get('total_checks', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0)}%")
        print()
        print("Breakdown:")
        print(f"  OK: {summary.get('ok', 0)}")
        print(f"  Warnings: {summary.get('warnings', 0)}")
        print(f"  Errors: {summary.get('errors', 0)}")
        print(f"  Critical: {summary.get('critical', 0)}")
        print()

        # Print module summaries
        for module_name, module_summary in summary.get('module_summaries', {}).items():
            status = module_summary.get('overall_status', 'Unknown')
            checks = module_summary.get('total_checks', 0)
            print(f"{module_name.upper():12} | {status:8} | {checks} checks")

        print("="*80)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="MAMcrawler Unified Diagnostic System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python diagnostic_system.py health                    # Full system health check
  python diagnostic_system.py abs                       # ABS diagnostics only
  python diagnostic_system.py monitor --interval 300   # Continuous monitoring
  python diagnostic_system.py report --format html     # Generate HTML report
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Health check command
    health_parser = subparsers.add_parser('health', help='Run full system health check')
    health_parser.add_argument('--modules', nargs='*',
                              choices=['abs', 'qbittorrent', 'vpn', 'mam', 'prowlarr', 'workflow', 'system'],
                              help='Specific modules to check (default: all)')

    # Individual module commands
    for module in ['abs', 'qbittorrent', 'vpn', 'mam', 'prowlarr', 'workflow', 'system']:
        module_parser = subparsers.add_parser(module, help=f'Run {module} diagnostics')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Run continuous monitoring')
    monitor_parser.add_argument('--interval', type=int, default=300,
                               help='Monitoring interval in seconds (default: 300)')
    monitor_parser.add_argument('--duration', type=int, default=3600,
                               help='Monitoring duration in seconds (default: 3600)')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate diagnostic report')
    report_parser.add_argument('--format', choices=['json', 'html'], default='json',
                              help='Report format (default: json)')
    report_parser.add_argument('--filename', help='Custom filename for report')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize diagnostic system
    system = DiagnosticSystem()

    try:
        if args.command == 'health':
            results = system.run_health_check(args.modules if hasattr(args, 'modules') and args.modules else None)
            system.print_summary(results)
            system.save_report(results)

        elif args.command in system.modules:
            result = system.run_single_module(args.command)
            print(f"\n{args.command.upper()} DIAGNOSTIC RESULTS:")
            print(f"Status: {result.get('overall_status', 'Unknown')}")
            print(f"Checks: {result.get('total_checks', 0)}")
            if 'results' in result:
                for r in result['results']:
                    status_icon = {'OK': '✓', 'WARNING': '⚠', 'ERROR': '✗', 'CRITICAL': '🚨'}.get(r['status'], '?')
                    print(f"  {status_icon} {r['component']}: {r['message']}")

        elif args.command == 'monitor':
            system.run_monitoring(args.interval, args.duration)

        elif args.command == 'report':
            # Run health check and save report
            results = system.run_health_check()
            filepath = system.save_report(results, args.filename, args.format)
            print(f"Report saved: {filepath}")

    except Exception as e:
        logger.error(f"Diagnostic system error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()