#!/usr/bin/env python3
"""
Test single book verification

Quick test to verify the audio extraction and transcription pipeline works
"""

import asyncio
import logging
import os
import json
from dotenv import load_dotenv
from audiobook_audio_verifier import VerificationController

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

ABS_URL = os.getenv('ABS_URL', 'http://localhost:13378')
ABS_TOKEN = os.getenv('ABS_TOKEN')


async def test_single_book():
    """Test verification on the first uncertain book"""

    # Load uncertain books
    with open('uncertain_books.json', 'r') as f:
        books = json.load(f)

    # Get unique books
    unique = list({b['id']: b for b in books}.values())

    if not unique:
        print("No books to test")
        return

    # Test first book
    test_book = unique[0]
    book_id = test_book['id']
    title = test_book['metadata']['title']

    print(f"\nTesting verification on:")
    print(f"  ID: {book_id}")
    print(f"  Title: {title}")
    print("")

    async with VerificationController(ABS_URL, ABS_TOKEN) as controller:
        result = await controller.verify_book(book_id, title)

        print("\n" + "="*80)
        print("VERIFICATION RESULT")
        print("="*80)
        print(f"Book ID: {result.book_id}")
        print(f"Current Title: {result.current_title}")
        print("")

        print(f"Audio Extraction: {'SUCCESS' if result.audio_extraction.success else 'FAILED'}")
        if result.audio_extraction.success:
            print(f"  Duration: {result.audio_extraction.duration}s")
        else:
            print(f"  Error: {result.audio_extraction.error}")
        print("")

        print(f"Transcription: {'SUCCESS' if result.transcription.success else 'FAILED'}")
        if result.transcription.success:
            print(f"  Text: {result.transcription.text}")
        else:
            print(f"  Error: {result.transcription.error}")
        print("")

        if result.parsed_metadata.title:
            print(f"Parsed Metadata:")
            print(f"  Title: {result.parsed_metadata.title}")
            print(f"  Author: {result.parsed_metadata.author}")
            if result.parsed_metadata.series_name:
                print(f"  Series: {result.parsed_metadata.series_name} #{result.parsed_metadata.sequence}")
            print("")

        if result.external_verification:
            print(f"External Verification (Goodreads):")
            print(f"  Title: {result.external_verification.title}")
            print(f"  Author: {result.external_verification.author}")
            if result.external_verification.series_name:
                print(f"  Series: {result.external_verification.series_name} #{result.external_verification.series_position}")
            print("")

        print(f"Final Confidence: {result.final_confidence*100:.1f}%")
        print(f"Updated: {'YES' if result.updated else 'NO'}")
        if result.update_error:
            print(f"Update Error: {result.update_error}")

        print("="*80)


if __name__ == "__main__":
    if not ABS_TOKEN:
        print("ERROR: ABS_TOKEN not set in .env file")
    else:
        asyncio.run(test_single_book())
