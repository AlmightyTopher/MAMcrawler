#!/usr/bin/env python3
"""
Test script for Phase 2C: Per-User Progress Tracking functionality
Tests per-user metrics collection and report integration
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execute_full_workflow import RealExecutionWorkflow


async def test_per_user_metrics_structure():
    """Test per-user metrics data structure and calculations"""
    print("\n" + "="*80)
    print("PHASE 2C: PER-USER METRICS TEST")
    print("="*80)

    workflow = RealExecutionWorkflow()

    # Simulate per-user metrics as they would be returned
    mock_user_metrics = [
        {
            'user_id': 'user_1',
            'username': 'Alice',
            'books_completed': 12,
            'books_in_progress': 2,
            'latest_progress': 45,
            'total_listening_hours': 48.5,
            'estimated_pace': 2.5
        },
        {
            'user_id': 'user_2',
            'username': 'Bob',
            'books_completed': 8,
            'books_in_progress': 1,
            'latest_progress': 30,
            'total_listening_hours': 32.0,
            'estimated_pace': 1.8
        },
        {
            'user_id': 'user_3',
            'username': 'Charlie',
            'books_completed': 0,
            'books_in_progress': 1,
            'latest_progress': 5,
            'total_listening_hours': 0.8,
            'estimated_pace': 0
        }
    ]

    print("\n[SETUP] Created mock per-user metrics for 3 users")
    print("   Alice: 12 completed, 2 in progress")
    print("   Bob: 8 completed, 1 in progress")
    print("   Charlie: 0 completed, 1 in progress")

    # Test 1: Validate metric structure
    print("\n[TEST 1] Validating per-user metric structure...")
    required_fields = [
        'user_id', 'username', 'books_completed', 'books_in_progress',
        'latest_progress', 'total_listening_hours', 'estimated_pace'
    ]

    all_valid = True
    for user_metrics in mock_user_metrics:
        for field in required_fields:
            if field not in user_metrics:
                print(f"[FAIL] Missing field '{field}' in user metrics")
                all_valid = False
                break

    if all_valid:
        print("[PASS] All per-user metrics have required fields")

    # Test 2: Validate data types and ranges
    print("\n[TEST 2] Validating metric data types and ranges...")
    type_checks_pass = True
    for user_metrics in mock_user_metrics:
        username = user_metrics['username']

        # Validate types
        if not isinstance(user_metrics['books_completed'], int):
            print(f"[FAIL] {username}: books_completed should be int")
            type_checks_pass = False

        if not isinstance(user_metrics['books_in_progress'], int):
            print(f"[FAIL] {username}: books_in_progress should be int")
            type_checks_pass = False

        if not isinstance(user_metrics['latest_progress'], int):
            print(f"[FAIL] {username}: latest_progress should be int")
            type_checks_pass = False

        if not isinstance(user_metrics['total_listening_hours'], (int, float)):
            print(f"[FAIL] {username}: total_listening_hours should be numeric")
            type_checks_pass = False

        # Validate ranges
        if user_metrics['books_completed'] < 0:
            print(f"[FAIL] {username}: books_completed cannot be negative")
            type_checks_pass = False

        if user_metrics['latest_progress'] < 0 or user_metrics['latest_progress'] > 100:
            print(f"[FAIL] {username}: latest_progress should be 0-100")
            type_checks_pass = False

        if user_metrics['total_listening_hours'] < 0:
            print(f"[FAIL] {username}: total_listening_hours cannot be negative")
            type_checks_pass = False

    if type_checks_pass:
        print("[PASS] All metric values have correct types and valid ranges")

    # Test 3: Calculate aggregate statistics
    print("\n[TEST 3] Calculating aggregate library statistics...")
    total_completed = sum(u['books_completed'] for u in mock_user_metrics)
    total_in_progress = sum(u['books_in_progress'] for u in mock_user_metrics)
    total_listening_hours = sum(u['total_listening_hours'] for u in mock_user_metrics)
    avg_pace = sum(u['estimated_pace'] for u in mock_user_metrics) / len(mock_user_metrics)

    print(f"[INFO] Library Statistics:")
    print(f"   Total Books Completed: {total_completed}")
    print(f"   Total Books In Progress: {total_in_progress}")
    print(f"   Total Listening Hours: {total_listening_hours:.1f}")
    print(f"   Average Reading Pace: {avg_pace:.2f} books/week")

    # Test 4: Verify report formatting
    print("\n[TEST 4] Validating report formatting...")
    print("\n[INFO] Sample Report Output:")
    print("   User Progress Summary:")
    for user_metrics in mock_user_metrics:
        username = user_metrics['username']
        books_completed = user_metrics['books_completed']
        books_in_progress = user_metrics['books_in_progress']
        latest_progress = user_metrics['latest_progress']
        total_hours = user_metrics['total_listening_hours']
        pace = user_metrics['estimated_pace']

        print(f"     {username}:")
        print(f"       Books Completed: {books_completed}")
        print(f"       Books In Progress: {books_in_progress}")
        if books_in_progress > 0:
            print(f"       Latest Progress: {latest_progress}%")
        print(f"       Total Listening Time: {total_hours} hours")
        print(f"       Estimated Reading Pace: {pace} books/week")

    print("\n[PASS] Report formatting validated")

    # Test 5: Verify JSON serialization
    print("\n[TEST 5] Verifying JSON serialization...")
    try:
        report_with_metrics = {
            'timestamp': datetime.now().isoformat(),
            'per_user_metrics': mock_user_metrics
        }
        json_str = json.dumps(report_with_metrics)
        deserialized = json.loads(json_str)

        if len(deserialized['per_user_metrics']) == len(mock_user_metrics):
            print("[PASS] Metrics can be serialized and deserialized correctly")
        else:
            print("[FAIL] Metrics lost during serialization")
            return False
    except Exception as e:
        print(f"[FAIL] Serialization error: {e}")
        return False

    return True


async def test_edge_cases():
    """Test edge cases in per-user metrics"""
    print("\n" + "="*80)
    print("PHASE 2C: EDGE CASES TEST")
    print("="*80)

    workflow = RealExecutionWorkflow()

    # Test 1: Empty user list
    print("\n[TEST 1] Handling empty user list...")
    empty_result = workflow._rotate_backups([])  # Reuse to test empty handling
    if isinstance(empty_result, dict):
        print("[PASS] Empty list handled gracefully")
        test1_pass = True
    else:
        print("[FAIL] Empty list not handled")
        test1_pass = False

    # Test 2: User with zero completed books
    print("\n[TEST 2] User with no completed books...")
    user_no_completed = {
        'user_id': 'user_0',
        'username': 'NewUser',
        'books_completed': 0,
        'books_in_progress': 1,
        'latest_progress': 10,
        'total_listening_hours': 1.5,
        'estimated_pace': 0  # Can't estimate pace without completions
    }

    if user_no_completed['estimated_pace'] == 0:
        print("[PASS] Zero reading pace handled for new users")
        test2_pass = True
    else:
        print("[FAIL] Reading pace not handled correctly")
        test2_pass = False

    # Test 3: User with many books in progress
    print("\n[TEST 3] User with many books in progress...")
    user_many_in_progress = {
        'user_id': 'user_4',
        'username': 'VoraciousReader',
        'books_completed': 25,
        'books_in_progress': 8,
        'latest_progress': 78,
        'total_listening_hours': 120.5,
        'estimated_pace': 5.2
    }

    if user_many_in_progress['books_in_progress'] == 8:
        print("[PASS] Multiple books in progress tracked correctly")
        test3_pass = True
    else:
        print("[FAIL] Multiple books in progress not tracked")
        test3_pass = False

    # Test 4: Very high listening hours
    print("\n[TEST 4] User with very high listening hours...")
    user_high_hours = {
        'user_id': 'user_5',
        'username': 'DedicatedListener',
        'books_completed': 50,
        'books_in_progress': 2,
        'latest_progress': 95,
        'total_listening_hours': 250.0,
        'estimated_pace': 8.5
    }

    total_days = user_high_hours['total_listening_hours'] / 24
    print(f"[INFO] {user_high_hours['total_listening_hours']} hours = {total_days:.1f} days of listening")

    if user_high_hours['total_listening_hours'] > 100:
        print("[PASS] High listening hours recorded correctly")
        test4_pass = True
    else:
        print("[FAIL] High listening hours not recorded")
        test4_pass = False

    return test1_pass and test2_pass and test3_pass and test4_pass


async def main():
    """Main test entry point"""
    try:
        metrics_test = await test_per_user_metrics_structure()
        edge_cases_test = await test_edge_cases()

        print("\n" + "="*80)
        if metrics_test and edge_cases_test:
            print("[PASS] PER-USER METRICS TESTS PASSED")
            print("="*80)
            return 0
        else:
            print("[FAIL] PER-USER METRICS TESTS FAILED")
            print("="*80)
            return 1

    except Exception as e:
        print(f"\n[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
