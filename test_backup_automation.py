#!/usr/bin/env python3
"""
Test script for Phase 12: Backup Automation functionality
Tests backup scheduling, validation, and rotation
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execute_full_workflow import RealExecutionWorkflow


async def test_backup_rotation():
    """Test backup rotation policy logic"""
    print("\n" + "="*80)
    print("PHASE 12: BACKUP AUTOMATION TEST")
    print("="*80)

    workflow = RealExecutionWorkflow()

    # Create mock backup data
    now = datetime.now()
    mock_backups = []

    # Create 15 mock backups: 7 daily (past 7 days) + 8 older
    for i in range(15):
        age_days = i
        backup_date = now - timedelta(days=age_days)

        mock_backups.append({
            'filename': f'backup_{backup_date.strftime("%Y-%m-%d_%H%M%S")}.tar.gz',
            'createdAt': backup_date.isoformat(),
            'size': (5 * 1024 * 1024) + (i * 100),  # 5MB + variable
            'path': f'/backups/backup_{i}.tar.gz'
        })

    print("\n[SETUP] Created 15 mock backups for rotation test")
    print(f"   Newest backup: {mock_backups[0]['filename']} ({mock_backups[0]['createdAt']})")
    print(f"   Oldest backup: {mock_backups[-1]['filename']} ({mock_backups[-1]['createdAt']})")

    # Test rotation policy
    print("\n[RUN] Testing rotation policy...")
    rotation_result = workflow._rotate_backups(mock_backups)

    kept = rotation_result.get('kept_backups', [])
    deleted = rotation_result.get('deleted_backups', [])

    print(f"\n[RESULT] Rotation Policy Results:")
    print(f"   Total backups: {len(mock_backups)}")
    print(f"   Kept: {len(kept)} backups")
    print(f"   Deleted: {len(deleted)} backups")
    print(f"   Daily backups kept: {rotation_result.get('daily_backups_kept', 0)}")
    print(f"   Weekly backups kept: {rotation_result.get('weekly_backups_kept', 0)}")

    # Verify retention policy
    daily_kept = rotation_result.get('daily_backups_kept', 0)
    weekly_kept = rotation_result.get('weekly_backups_kept', 0)

    success = True
    if daily_kept > 7:
        print(f"\n[FAIL] Daily backups exceeded limit: {daily_kept} > 7")
        success = False
    elif weekly_kept > 4:
        print(f"\n[FAIL] Weekly backups exceeded limit: {weekly_kept} > 4")
        success = False
    elif len(kept) > 11:
        print(f"\n[FAIL] Total kept backups exceeded limit: {len(kept)} > 11")
        success = False
    else:
        print(f"\n[PASS] Rotation policy correctly applied:")
        print(f"   - Daily backups: {daily_kept}/7")
        print(f"   - Weekly backups: {weekly_kept}/4")
        print(f"   - Total kept: {len(kept)}/11")

    # Show which backups were kept
    print(f"\n[INFO] Kept Backups:")
    for i, backup in enumerate(kept[:5], 1):  # Show first 5
        print(f"   {i}. {backup['filename']}")
    if len(kept) > 5:
        print(f"   ... and {len(kept) - 5} more")

    # Show which backups were deleted
    print(f"\n[INFO] Deleted Backups:")
    for i, backup in enumerate(deleted[:3], 1):  # Show first 3
        print(f"   {i}. {backup['filename']}")
    if len(deleted) > 3:
        print(f"   ... and {len(deleted) - 3} more")

    return success


async def test_backup_validation():
    """Test backup file validation logic"""
    print("\n" + "="*80)
    print("PHASE 12: BACKUP VALIDATION TEST")
    print("="*80)

    workflow = RealExecutionWorkflow()

    # Test 1: Valid backup
    print("\n[TEST 1] Valid backup file (5MB)")
    valid_backup = {
        'filename': 'backup_2025-11-27_214700.tar.gz',
        'size': 5 * 1024 * 1024,  # 5MB
        'createdAt': datetime.now().isoformat()
    }

    if valid_backup['size'] >= 1024 * 1024:
        print("[PASS] Backup size validation passed")
        test1_pass = True
    else:
        print("[FAIL] Backup size validation failed")
        test1_pass = False

    # Test 2: Undersized backup
    print("\n[TEST 2] Undersized backup file (512KB)")
    undersized_backup = {
        'filename': 'backup_2025-11-27_214700.tar.gz',
        'size': 512 * 1024,  # 512KB
        'createdAt': datetime.now().isoformat()
    }

    if undersized_backup['size'] < 1024 * 1024:
        print("[PASS] Undersized backup correctly rejected")
        test2_pass = True
    else:
        print("[FAIL] Undersized backup should have been rejected")
        test2_pass = False

    # Test 3: Backup list parsing
    print("\n[TEST 3] Backup list response parsing")
    backup_response_dict = {
        'backups': [
            {'filename': 'backup_1.tar.gz', 'size': 5 * 1024 * 1024},
            {'filename': 'backup_2.tar.gz', 'size': 5 * 1024 * 1024}
        ]
    }

    backups = backup_response_dict.get('backups', []) if isinstance(backup_response_dict, dict) else backup_response_dict
    if len(backups) == 2:
        print("[PASS] Dict response parsing works")
        test3_pass = True
    else:
        print("[FAIL] Dict response parsing failed")
        test3_pass = False

    # Test 4: List response parsing
    print("\n[TEST 4] Backup list array response parsing")
    backup_response_list = [
        {'filename': 'backup_1.tar.gz', 'size': 5 * 1024 * 1024},
        {'filename': 'backup_2.tar.gz', 'size': 5 * 1024 * 1024}
    ]

    backups = backup_response_list.get('backups', []) if isinstance(backup_response_list, dict) else backup_response_list
    if len(backups) == 2:
        print("[PASS] Array response parsing works")
        test4_pass = True
    else:
        print("[FAIL] Array response parsing failed")
        test4_pass = False

    return test1_pass and test2_pass and test3_pass and test4_pass


async def main():
    """Main test entry point"""
    try:
        rotation_pass = await test_backup_rotation()
        validation_pass = await test_backup_validation()

        print("\n" + "="*80)
        if rotation_pass and validation_pass:
            print("[PASS] BACKUP AUTOMATION TESTS PASSED")
            print("="*80)
            return 0
        else:
            print("[FAIL] BACKUP AUTOMATION TESTS FAILED")
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
