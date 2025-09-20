#!/usr/bin/env python
"""
Test script for the voice processing pipeline.
Tests FFmpeg availability, segmentation, and basic pipeline flow.
"""

import os
import sys
import django
import tempfile
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voicenote_backend.settings')
django.setup()

from records.services import (
    verify_ffmpeg_availability,
    get_audio_duration,
    split_to_segments,
    cleanup_segments,
    merge_transcripts
)


def test_ffmpeg_availability():
    """Test that FFmpeg and ffprobe are available."""
    print("Testing FFmpeg availability...")
    result = verify_ffmpeg_availability()
    if result:
        print("✓ FFmpeg and ffprobe are available")
    else:
        print("✗ FFmpeg/ffprobe not found")
    return result


def test_audio_duration():
    """Test getting audio duration from a test file."""
    print("\nTesting audio duration detection...")
    
    # Check if we have any test audio files
    test_files = [
        '/workspace/media/voices/2025/09/20/test_audio.m4a',
        '/workspace/media/voices/2025/09/20/test_audio_lVJiGr0.m4a',
        '/workspace/media/voices/2025/09/20/test_audio_QsvJ6l8.m4a'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"  Testing with: {test_file}")
            duration = get_audio_duration(test_file)
            if duration is not None:
                print(f"  ✓ Duration: {duration} seconds")
                return True
            else:
                print(f"  ✗ Could not get duration")
    
    print("  ℹ No test audio files found in media/voices/")
    return False


def test_segmentation():
    """Test audio segmentation."""
    print("\nTesting audio segmentation...")
    
    # Find a test audio file
    test_files = [
        '/workspace/media/voices/2025/09/20/test_audio.m4a',
        '/workspace/media/voices/2025/09/20/test_audio_lVJiGr0.m4a',
        '/workspace/media/voices/2025/09/20/test_audio_QsvJ6l8.m4a'
    ]
    
    test_file = None
    for f in test_files:
        if os.path.exists(f):
            test_file = f
            break
    
    if not test_file:
        print("  ℹ No test audio file available for segmentation test")
        return False
    
    try:
        print(f"  Testing segmentation with: {test_file}")
        segments = split_to_segments(test_file, segment_seconds=30)  # Use 30s for testing
        
        print(f"  ✓ Created {len(segments)} segments:")
        for seg in segments:
            print(f"    - Segment {seg['index']+1}: {seg['start_time']}s-{seg['end_time']}s")
            print(f"      Path: {seg['path']}")
            print(f"      Extraction time: {seg.get('extraction_time', 0):.2f}s")
        
        # Clean up test segments
        cleanup_segments(segments, os.path.dirname(segments[0]['path']) if segments else None)
        print("  ✓ Cleaned up test segments")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Segmentation failed: {e}")
        return False


def test_transcript_merging():
    """Test transcript merging functionality."""
    print("\nTesting transcript merging...")
    
    # Test with sample transcripts
    test_transcripts = [
        "این اولین قسمت از متن است.",
        "قسمت دوم ادامه دارد.",
        "[SEGMENT FAILED]",
        "و این آخرین قسمت است."
    ]
    
    merged = merge_transcripts(test_transcripts)
    
    print("  Input segments:")
    for i, t in enumerate(test_transcripts):
        print(f"    {i+1}. {t}")
    
    print("\n  Merged output:")
    print(f"    {merged[:100]}..." if len(merged) > 100 else f"    {merged}")
    print(f"  ✓ Merged {len(test_transcripts)} segments into {len(merged)} characters")
    
    return True


def test_environment_variables():
    """Test that required environment variables are set."""
    print("\nTesting environment configuration...")
    
    from django.conf import settings
    
    configs = {
        'OPENAI_API_KEY': getattr(settings, 'OPENAI_API_KEY', None),
        'OPENAI_BASE_URL': getattr(settings, 'OPENAI_BASE_URL', None),
        'ASR_MODEL': getattr(settings, 'ASR_MODEL', None),
        'SEGMENT_SECONDS': getattr(settings, 'SEGMENT_SECONDS', None),
    }
    
    all_set = True
    for key, value in configs.items():
        if value:
            if key == 'OPENAI_API_KEY':
                print(f"  ✓ {key}: ***{value[-4:] if len(value) > 4 else '***'}")
            else:
                print(f"  ✓ {key}: {value}")
        else:
            print(f"  ✗ {key}: Not set")
            all_set = False
    
    if configs.get('OPENAI_API_KEY') == 'test-key-replace-with-real':
        print("  ⚠ Warning: Using test API key. Replace with real key for actual ASR.")
    
    return all_set


def main():
    """Run all tests."""
    print("=" * 60)
    print("Voice Processing Pipeline Test Suite")
    print("=" * 60)
    
    results = {
        'FFmpeg': test_ffmpeg_availability(),
        'Environment': test_environment_variables(),
        'Duration': test_audio_duration(),
        'Segmentation': test_segmentation(),
        'Merging': test_transcript_merging(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All tests passed!")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())