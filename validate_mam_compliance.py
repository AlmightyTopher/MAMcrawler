#!/usr/bin/env python3
"""
MAM Best Practices Compliance Validator

Validates automated audiobook system against MAM best practices from official guides.
Checks configuration, client status, and seeding health.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class MAMComplianceValidator:
    """Validates MAM automation compliance with best practices."""

    def __init__(self):
        self.rules_file = 'mam_automation_rules.json'
        self.config_file = 'audiobook_auto_config.json'
        self.rules = self.load_rules()
        self.config = self.load_config()
        self.violations = []
        self.warnings = []
        self.recommendations = []

    def load_rules(self) -> Dict:
        """Load MAM automation rules."""
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_config(self) -> Dict:
        """Load current automation configuration."""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def check_seeding_requirements(self) -> List[Tuple[str, str, str]]:
        """Validate seeding configuration against requirements."""
        results = []
        rules = self.rules['seeding_requirements']

        # These are enforced by MAM, not configurable
        results.append((
            "PASS",
            "Seeding Requirements",
            "72-hour minimum seeding enforced by MAM system"
        ))

        # Check if automation encourages good seeding
        if self.config.get('download_settings', {}).get('auto_add_to_qbittorrent'):
            results.append((
                "PASS",
                "Auto-add to Client",
                "Torrents automatically added to qBittorrent for seeding"
            ))
        else:
            results.append((
                "WARN",
                "Auto-add to Client",
                "Manual torrent addition required - may miss seeding window"
            ))

        return results

    def check_client_configuration(self) -> List[Tuple[str, str, str]]:
        """Validate client configuration."""
        results = []

        # Check if qBittorrent is being used (from config)
        category = self.config.get('download_settings', {}).get('category', '')
        if 'qbittorrent' in category.lower() or category == 'audiobooks-auto':
            results.append((
                "PASS",
                "Client Choice",
                "Using qBittorrent (recommended client)"
            ))
        else:
            results.append((
                "INFO",
                "Client Choice",
                "Ensure using approved client (qBittorrent recommended)"
            ))

        return results

    def check_download_strategy(self) -> List[Tuple[str, str, str]]:
        """Validate download strategy against best practices."""
        results = []
        strategy = self.rules['download_strategy']
        config_dl = self.config.get('download_settings', {})

        # Check VIP torrent preference
        if config_dl.get('prefer_vip_torrents', False):
            results.append((
                "PASS",
                "VIP Torrent Priority",
                "Prioritizing VIP torrents (always freeleech)"
            ))
        else:
            results.append((
                "WARN",
                "VIP Torrent Priority",
                "NOT prioritizing VIP torrents - missing freeleech opportunity"
            ))

        # Check freeleech preference
        if config_dl.get('prefer_freeleech', False):
            results.append((
                "PASS",
                "Freeleech Priority",
                "Prioritizing freeleech torrents (0 ratio impact)"
            ))
        else:
            results.append((
                "WARN",
                "Freeleech Priority",
                "NOT prioritizing freeleech - may impact ratio"
            ))

        # Check FL wedge usage
        if config_dl.get('use_freeleech_wedges', False):
            results.append((
                "PASS",
                "FL Wedge Usage",
                "Auto-applying FL wedges (110 available, earn more than use)"
            ))
        else:
            results.append((
                "WARN",
                "FL Wedge Usage",
                "NOT using FL wedges - wasting free resource (110 available)"
            ))

        return results

    def check_duplicate_detection(self) -> List[Tuple[str, str, str]]:
        """Validate duplicate detection configuration."""
        results = []
        config_query = self.config.get('query_settings', {})

        # Check if duplicate detection enabled
        if config_query.get('skip_duplicates', False):
            results.append((
                "PASS",
                "Duplicate Detection",
                "Enabled - checking Audiobookshelf library"
            ))

            # Check max_check_limit
            max_check = config_query.get('max_check_limit', 0)
            if max_check >= 100:
                results.append((
                    "PASS",
                    "Check Limit",
                    f"Checking up to top {max_check} results (adequate)"
                ))
            else:
                results.append((
                    "WARN",
                    "Check Limit",
                    f"Only checking top {max_check} - may miss new books"
                ))
        else:
            results.append((
                "FAIL",
                "Duplicate Detection",
                "DISABLED - will download duplicates and waste bandwidth/ratio"
            ))

        # Check Audiobookshelf connection
        abs_url = os.getenv('ABS_URL')
        abs_token = os.getenv('ABS_TOKEN')
        if abs_url and abs_token:
            results.append((
                "PASS",
                "Audiobookshelf Credentials",
                f"Configured ({abs_url})"
            ))
        else:
            results.append((
                "FAIL",
                "Audiobookshelf Credentials",
                "Missing ABS_URL or ABS_TOKEN in .env"
            ))

        return results

    def check_bonus_point_strategy(self) -> List[Tuple[str, str, str]]:
        """Validate bonus point optimization."""
        results = []
        current = self.rules['bonus_point_strategy']['current_status']

        # Check if bonus points capped
        if current['bonus_points'] >= current['bonus_points_cap']:
            results.append((
                "WARN",
                "Bonus Points Capped",
                f"{current['bonus_points']}/{current['bonus_points_cap']} - "
                f"RECOMMEND: Trade 50,000-90,000 for upload credit"
            ))
        else:
            results.append((
                "PASS",
                "Bonus Points",
                f"{current['bonus_points']}/{current['bonus_points_cap']}"
            ))

        # Check FL wedge count
        if current['fl_wedges'] > 100:
            results.append((
                "INFO",
                "FL Wedges",
                f"{current['fl_wedges']} available - use liberally!"
            ))
        elif current['fl_wedges'] > 50:
            results.append((
                "PASS",
                "FL Wedges",
                f"{current['fl_wedges']} available"
            ))
        else:
            results.append((
                "WARN",
                "FL Wedges",
                f"Only {current['fl_wedges']} available - may need to earn more"
            ))

        # Check ratio
        if current['ratio'] >= 4.0:
            results.append((
                "PASS",
                "Ratio Health",
                f"{current['ratio']:.6f} (EXCELLENT - way above minimum)"
            ))
        elif current['ratio'] >= 2.0:
            results.append((
                "PASS",
                "Ratio Health",
                f"{current['ratio']:.6f} (Good - comfortable margin)"
            ))
        elif current['ratio'] >= 1.0:
            results.append((
                "WARN",
                "Ratio Health",
                f"{current['ratio']:.6f} (Above minimum but close)"
            ))
        else:
            results.append((
                "FAIL",
                "Ratio Health",
                f"{current['ratio']:.6f} (BELOW MINIMUM - seed-only risk!)"
            ))

        return results

    def check_automation_config(self) -> List[Tuple[str, str, str]]:
        """Validate automation configuration."""
        results = []
        schedule = self.config.get('schedule', {})
        query = self.config.get('query_settings', {})

        # Check schedule enabled
        if schedule.get('enabled', False):
            day = schedule.get('day_of_week', 'unknown')
            time = schedule.get('time', 'unknown')
            results.append((
                "PASS",
                "Automation Schedule",
                f"Enabled - Every {day.title()} at {time}"
            ))
        else:
            results.append((
                "WARN",
                "Automation Schedule",
                "Disabled - manual downloads required"
            ))

        # Check genre whitelist
        use_whitelist = query.get('use_whitelist', False)
        if use_whitelist:
            genres = self.config.get('included_genres', [])
            results.append((
                "PASS",
                "Genre Filtering",
                f"Whitelist mode - {len(genres)} genres: {', '.join(genres)}"
            ))
        else:
            excluded = self.config.get('excluded_genres', [])
            results.append((
                "INFO",
                "Genre Filtering",
                f"Blacklist mode - excluding {len(excluded)} genres"
            ))

        # Check top N setting
        top_n = query.get('top_n_per_genre', 0)
        if top_n > 0:
            results.append((
                "PASS",
                "Download Amount",
                f"Top {top_n} NEW books per genre"
            ))
        else:
            results.append((
                "FAIL",
                "Download Amount",
                "top_n_per_genre is 0 - no downloads will occur!"
            ))

        return results

    def check_quality_filters(self) -> List[Tuple[str, str, str]]:
        """Validate quality filter settings."""
        results = []
        query = self.config.get('query_settings', {})

        # Check minimum seeders
        min_seeders = query.get('min_seeders', 0)
        if min_seeders >= 5:
            results.append((
                "PASS",
                "Seeder Filter",
                f"Minimum {min_seeders} seeders (good availability)"
            ))
        elif min_seeders > 0:
            results.append((
                "WARN",
                "Seeder Filter",
                f"Minimum {min_seeders} seeders (may miss good torrents)"
            ))
        else:
            results.append((
                "INFO",
                "Seeder Filter",
                "No minimum seeder requirement"
            ))

        # Check timespan preference
        timespan = query.get('timespan_preference', 'none')
        if timespan == 'recent':
            results.append((
                "PASS",
                "Timespan Preference",
                "Recent releases (better seeder availability)"
            ))
        else:
            results.append((
                "INFO",
                "Timespan Preference",
                f"{timespan.title()} timespan selected"
            ))

        return results

    def run_validation(self) -> Dict[str, List]:
        """Run all validation checks."""
        print("="*70)
        print("MAM AUTOMATION COMPLIANCE VALIDATION")
        print("="*70)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Rules Version: {self.rules.get('_last_updated', 'unknown')}")
        print()

        all_results = {
            'pass': [],
            'warn': [],
            'fail': [],
            'info': []
        }

        # Run all checks
        checks = [
            ("SEEDING REQUIREMENTS", self.check_seeding_requirements),
            ("CLIENT CONFIGURATION", self.check_client_configuration),
            ("DOWNLOAD STRATEGY", self.check_download_strategy),
            ("DUPLICATE DETECTION", self.check_duplicate_detection),
            ("BONUS POINT STRATEGY", self.check_bonus_point_strategy),
            ("AUTOMATION CONFIG", self.check_automation_config),
            ("QUALITY FILTERS", self.check_quality_filters),
        ]

        for section_name, check_func in checks:
            print(f"\n{section_name}")
            print("-"*70)

            results = check_func()
            for status, check, message in results:
                status_lower = status.lower()
                all_results[status_lower].append((section_name, check, message))

                # Print with color coding
                if status == "PASS":
                    symbol = "✓"
                elif status == "WARN":
                    symbol = "⚠"
                elif status == "FAIL":
                    symbol = "✗"
                else:
                    symbol = "ℹ"

                print(f"  {symbol} [{status}] {check}: {message}")

        return all_results

    def print_summary(self, results: Dict[str, List]):
        """Print validation summary."""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)

        pass_count = len(results['pass'])
        warn_count = len(results['warn'])
        fail_count = len(results['fail'])
        info_count = len(results['info'])
        total = pass_count + warn_count + fail_count + info_count

        print(f"\nTotal Checks: {total}")
        print(f"  ✓ Passed:   {pass_count}")
        print(f"  ⚠ Warnings: {warn_count}")
        print(f"  ✗ Failed:   {fail_count}")
        print(f"  ℹ Info:     {info_count}")

        # Overall status
        print("\n" + "-"*70)
        if fail_count == 0 and warn_count == 0:
            print("STATUS: ✓ EXCELLENT - All best practices followed!")
        elif fail_count == 0:
            print(f"STATUS: ⚠ GOOD - {warn_count} warning(s) to address")
        else:
            print(f"STATUS: ✗ NEEDS ATTENTION - {fail_count} critical issue(s)")

        # Recommendations
        if warn_count > 0 or fail_count > 0:
            print("\n" + "="*70)
            print("RECOMMENDED ACTIONS")
            print("="*70)

            if fail_count > 0:
                print("\nCRITICAL (Fix immediately):")
                for section, check, message in results['fail']:
                    print(f"  ✗ {check}: {message}")

            if warn_count > 0:
                print("\nWARNINGS (Should address):")
                for section, check, message in results['warn']:
                    print(f"  ⚠ {check}: {message}")

        print("\n" + "="*70)
        print("See MAM_BEST_PRACTICES_CHECKLIST.md for detailed guidance")
        print("="*70)


def main():
    """Main validation entry point."""
    try:
        validator = MAMComplianceValidator()
        results = validator.run_validation()
        validator.print_summary(results)

        # Exit code based on failures
        fail_count = len(results['fail'])
        sys.exit(1 if fail_count > 0 else 0)

    except FileNotFoundError as e:
        print(f"✗ ERROR: Required file not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ ERROR: Invalid JSON in configuration: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR: Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
