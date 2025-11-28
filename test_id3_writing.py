#!/usr/bin/env python3
"""
Test script for Phase 2A: ID3 Tag Writing functionality
Tests ID3 metadata writing to sample audio files
"""

import os
import sys
import asyncio
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execute_full_workflow import RealExecutionWorkflow


async def setup_test_library():
    """Create a test library structure with sample MP3 files"""
    test_dir = tempfile.mkdtemp(prefix="id3_test_")

    # Create folder structure: /test/Author/Series/Book Title {Narrator}/file.mp3
    book_path = os.path.join(
        test_dir,
        "Brandon Sanderson",
        "Stormlight Archive",
        "The Way of Kings {Michael Kramer}"
    )
    os.makedirs(book_path, exist_ok=True)

    # Create a minimal valid MP3 file (ID3 header + minimal MPEG frame)
    mp3_file = os.path.join(book_path, "chapter01.mp3")

    # Minimal ID3v2.4 header + empty frame
    id3_header = (
        b'ID3'           # ID3 identifier
        b'\x04\x00'      # Version 2.4.0
        b'\x00'          # Flags (no unsync, no extended header, no experimental)
        b'\x00\x00\x00\x00'  # Size (0 bytes of frames)
    )

    # Minimal MPEG frame (just a sync word)
    mpeg_frame = b'\xff\xfb' + b'\x00' * 100  # Sync word + dummy data

    with open(mp3_file, 'wb') as f:
        f.write(id3_header)
        f.write(mpeg_frame)

    print(f"[OK] Created test library at: {test_dir}")
    print(f"   Structure: {book_path}")
    print(f"   File: {mp3_file}")

    return test_dir, mp3_file


async def test_id3_writing():
    """Test ID3 tag writing functionality"""
    print("\n" + "="*80)
    print("PHASE 2A: ID3 TAG WRITING TEST")
    print("="*80)

    # Setup test library
    test_dir, mp3_file = await setup_test_library()

    try:
        # Create workflow instance
        workflow = RealExecutionWorkflow()

        print("\n[RUN] Running ID3 tag writing...")
        print(f"   Library path: {test_dir}")

        # Run ID3 writing
        result = await workflow.write_id3_metadata_to_audio_files(library_path=test_dir)

        # Display results
        print("\n[STATS] ID3 Writing Results:")
        print(f"   Written: {result.get('written', 0)} files")
        print(f"   Failed: {result.get('failed', 0)} files")
        print(f"   Skipped: {result.get('skipped', 0)} files")

        # Verify tags were written
        print("\n[INFO] Verifying written tags...")
        try:
            from mutagen.easyid3 import EasyID3

            audio = EasyID3(mp3_file)

            print(f"   Title: {audio.get('title', ['Not set'])[0]}")
            print(f"   Artist (Narrator): {audio.get('artist', ['Not set'])[0]}")
            print(f"   Album Artist (Author): {audio.get('albumartist', ['Not set'])[0]}")
            print(f"   Album (Series): {audio.get('album', ['Not set'])[0]}")

            # Verify narrator was extracted from folder name
            if 'Michael Kramer' in audio.get('artist', [''])[0]:
                print("\n[PASS] Narrator correctly extracted from folder name {Michael Kramer}")
            else:
                print("\n[WARN] Narrator may not be correctly extracted")

        except Exception as e:
            print(f"   Error reading tags: {e}")

        # Return success
        return result.get('written', 0) > 0

    finally:
        # Cleanup
        print(f"\n[CLEANUP] Cleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)


async def main():
    """Main test entry point"""
    try:
        success = await test_id3_writing()

        print("\n" + "="*80)
        if success:
            print("[PASS] ID3 TAG WRITING TEST PASSED")
            print("="*80)
            return 0
        else:
            print("[FAIL] ID3 TAG WRITING TEST FAILED")
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
