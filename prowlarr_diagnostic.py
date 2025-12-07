#!/usr/bin/env python3
"""
Prowlarr Diagnostic and Troubleshooting Script
=============================================

Comprehensive diagnostics for Prowlarr to identify and fix issues preventing
audiobook searches from working.
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

from dotenv import load_dotenv
load_dotenv()

import requests
from backend.integrations.qbittorrent_client import QBittorrentClient

class ProwlarrDiagnostic:
    """Comprehensive Prowlarr diagnostics and troubleshooting"""

    def __init__(self):
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_api_key = os.getenv('PROWLARR_API_KEY')

        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.prowlarr_api_key,
            'Content-Type': 'application/json'
        })

        self.results = {
            "health_check": {},
            "system_status": {},
            "indexers": {},
            "test_searches": {},
            "recommendations": []
        }

    def check_health(self) -> Dict[str, Any]:
        """Check Prowlarr health status"""
        print("Checking Prowlarr health...")

        try:
            response = self.session.get(f"{self.prowlarr_url}/api/v1/health", timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                self.results["health_check"] = {
                    "status": "OK",
                    "response_code": response.status_code,
                    "data": health_data
                }
                print("✓ Prowlarr health check passed")
                return self.results["health_check"]
            else:
                self.results["health_check"] = {
                    "status": "ERROR",
                    "response_code": response.status_code,
                    "error": f"HTTP {response.status_code}"
                }
                print(f"✗ Prowlarr health check failed: HTTP {response.status_code}")
                return self.results["health_check"]

        except Exception as e:
            self.results["health_check"] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ Prowlarr health check failed: {e}")
            return self.results["health_check"]

    def get_system_status(self) -> Dict[str, Any]:
        """Get Prowlarr system status"""
        print("Getting Prowlarr system status...")

        try:
            response = self.session.get(f"{self.prowlarr_url}/api/v1/system/status", timeout=10)

            if response.status_code == 200:
                status_data = response.json()
                self.results["system_status"] = {
                    "status": "OK",
                    "data": status_data
                }
                print("✓ System status retrieved")
                return self.results["system_status"]
            else:
                self.results["system_status"] = {
                    "status": "ERROR",
                    "response_code": response.status_code
                }
                print(f"✗ System status failed: HTTP {response.status_code}")
                return self.results["system_status"]

        except Exception as e:
            self.results["system_status"] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ System status failed: {e}")
            return self.results["system_status"]

    def get_indexers(self) -> Dict[str, Any]:
        """Get configured indexers"""
        print("Getting configured indexers...")

        try:
            response = self.session.get(f"{self.prowlarr_url}/api/v1/indexer", timeout=10)

            if response.status_code == 200:
                indexers = response.json()
                self.results["indexers"] = {
                    "status": "OK",
                    "count": len(indexers),
                    "indexers": indexers
                }
                print(f"✓ Found {len(indexers)} indexers")

                # Analyze indexers
                enabled_indexers = [idx for idx in indexers if idx.get('enable', False)]
                audiobook_indexers = [idx for idx in indexers if 'audiobook' in idx.get('categories', []) or 'book' in idx.get('categories', [])]

                print(f"  - Enabled: {len(enabled_indexers)}")
                print(f"  - Audiobook-capable: {len(audiobook_indexers)}")

                return self.results["indexers"]
            else:
                self.results["indexers"] = {
                    "status": "ERROR",
                    "response_code": response.status_code
                }
                print(f"✗ Indexer retrieval failed: HTTP {response.status_code}")
                return self.results["indexers"]

        except Exception as e:
            self.results["indexers"] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ Indexer retrieval failed: {e}")
            return self.results["indexers"]

    def test_search(self, query: str, category: str = None) -> Dict[str, Any]:
        """Test a search query"""
        print(f"Testing search: '{query}'")

        search_url = f"{self.prowlarr_url}/api/v1/search?query={requests.utils.quote(query)}&type=search"

        if category:
            search_url += f"&category={category}"

        try:
            response = self.session.get(search_url, timeout=30)

            if response.status_code == 200:
                results = response.json()
                result_data = {
                    "query": query,
                    "status": "OK",
                    "result_count": len(results),
                    "results": results[:5]  # First 5 results for brevity
                }
                print(f"✓ Search returned {len(results)} results")
                return result_data
            else:
                result_data = {
                    "query": query,
                    "status": "ERROR",
                    "response_code": response.status_code
                }
                print(f"✗ Search failed: HTTP {response.status_code}")
                return result_data

        except Exception as e:
            result_data = {
                "query": query,
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ Search failed: {e}")
            return result_data

    def run_diagnostics(self):
        """Run complete diagnostic suite"""
        print("=" * 80)
        print("PROWLARR DIAGNOSTIC SUITE")
        print("=" * 80)
        print(f"Start: {datetime.now().isoformat()}")
        print(f"Prowlarr URL: {self.prowlarr_url}")
        print()

        # Step 1: Health check
        print("1. HEALTH CHECK")
        print("-" * 40)
        health = self.check_health()
        print()

        if health["status"] != "OK":
            print("❌ CRITICAL: Prowlarr is not healthy. Cannot proceed with diagnostics.")
            self.generate_recommendations()
            return

        # Step 2: System status
        print("2. SYSTEM STATUS")
        print("-" * 40)
        system_status = self.get_system_status()
        print()

        # Step 3: Indexers
        print("3. INDEXER CONFIGURATION")
        print("-" * 40)
        indexers = self.get_indexers()
        print()

        # Step 4: Test searches
        print("4. SEARCH TESTS")
        print("-" * 40)

        test_queries = [
            "test",  # Basic connectivity test
            "audiobook",  # Audiobook category test
            "The Name of the Wind audiobook",  # Specific book test
            "Dune audiobook",  # Another book test
        ]

        for query in test_queries:
            result = self.test_search(query)
            self.results["test_searches"][query] = result
            print()

        # Step 5: Generate recommendations
        print("5. DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
        print("-" * 40)
        self.generate_recommendations()

        # Save results
        self.save_report()

        print("\n" + "=" * 80)
        print("DIAGNOSTICS COMPLETE")
        print("=" * 80)

    def generate_recommendations(self):
        """Generate troubleshooting recommendations based on results"""

        recommendations = []

        # Health check issues
        if self.results["health_check"].get("status") != "OK":
            recommendations.append({
                "priority": "CRITICAL",
                "issue": "Prowlarr health check failed",
                "solution": "Check if Prowlarr service is running and accessible at the configured URL"
            })

        # Indexer issues
        indexers = self.results.get("indexers", {})
        if indexers.get("status") == "OK":
            indexer_list = indexers.get("indexers", [])
            enabled_count = len([idx for idx in indexer_list if idx.get('enable', False)])
            audiobook_count = len([idx for idx in indexer_list if 'audiobook' in str(idx.get('categories', [])) or 'book' in str(idx.get('categories', []))])

            if enabled_count == 0:
                recommendations.append({
                    "priority": "CRITICAL",
                    "issue": "No indexers are enabled",
                    "solution": "Enable at least one indexer in Prowlarr settings"
                })

            if audiobook_count == 0:
                recommendations.append({
                    "priority": "HIGH",
                    "issue": "No audiobook-capable indexers configured",
                    "solution": "Add and enable indexers that support audiobook categories (e.g., 1337x, RARBG, The Pirate Bay)"
                })

        # Search test issues
        test_searches = self.results.get("test_searches", {})
        failed_searches = [q for q, r in test_searches.items() if r.get("status") != "OK"]
        zero_results = [q for q, r in test_searches.items() if r.get("result_count", 0) == 0 and r.get("status") == "OK"]

        if failed_searches:
            recommendations.append({
                "priority": "HIGH",
                "issue": f"Search queries failed: {', '.join(failed_searches)}",
                "solution": "Check indexer configurations and API keys. Test indexers individually in Prowlarr UI."
            })

        if zero_results:
            recommendations.append({
                "priority": "MEDIUM",
                "issue": f"Searches returning zero results: {', '.join(zero_results)}",
                "solution": "Indexers may not support these categories or queries. Try different indexers or check indexer capabilities."
            })

        # General recommendations
        recommendations.extend([
            {
                "priority": "LOW",
                "issue": "Test indexer connectivity",
                "solution": "In Prowlarr UI, go to Indexers and click 'Test' on each enabled indexer"
            },
            {
                "priority": "LOW",
                "issue": "Check indexer categories",
                "solution": "Ensure indexers have audiobook/book categories enabled in their settings"
            }
        ])

        self.results["recommendations"] = recommendations

        # Print recommendations
        if recommendations:
            print("RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"[{rec['priority']}] {rec['issue']}")
                print(f"  → {rec['solution']}")
                print()
        else:
            print("✓ No issues detected - Prowlarr appears to be working correctly")

    def save_report(self):
        """Save diagnostic report"""
        report_file = f"prowlarr_diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            print(f"Report saved: {report_file}")
        except Exception as e:
            print(f"Could not save report: {e}")


def main():
    diagnostic = ProwlarrDiagnostic()
    diagnostic.run_diagnostics()


if __name__ == '__main__':
    main()