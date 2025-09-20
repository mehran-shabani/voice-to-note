"""
Service functions for processing voice recordings with FFmpeg segmentation and Whisper ASR.
"""
import os
import logging
import subprocess
import tempfile
import time
import asyncio
import concurrent.futures
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI
from .models import VoiceRecording, VoiceNote

logger = logging.getLogger(__name__)

# Persian guidance prompt for Whisper ASR (must match agent.md verbatim)
WHISPER_PROMPT = """متن این فایل صوتی مربوط به یک جلسهٔ آموزشی به زبان فارسی است.
لطفاً واژگان را با املای رایج فارسی بنویس و اعداد را به صورت رقم ثبت کن.
نام‌های علمی و اصطلاحات را همان‌گونه که ادا می‌شود ثبت کن.
از حدس‌زدن یا افزودن کلمات خودداری کن؛ فقط آنچه گفته می‌شود را بنویس."""

# Maximum concurrent ASR requests
MAX_CONCURRENT_ASR = 3


def verify_ffmpeg_availability() -> bool:
    """
    Verify that ffmpeg and ffprobe are available in the system.
    
    Returns:
        True if both tools are available, False otherwise
    """
    tools = ['ffmpeg', 'ffprobe']
    for tool in tools:
        try:
            result = subprocess.run(
                [tool, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error(f"{tool} not available or not working properly")
                return False
            logger.info(f"{tool} is available: {result.stdout.split('\\n')[0]}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"{tool} not found in PATH: {e}")
            return False
    return True


def store_voice_file(uploaded_file) -> VoiceRecording:
    """
    Store an uploaded voice file and create a VoiceRecording instance.
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Returns:
        VoiceRecording instance with status='uploaded'
    """
    voice_recording = VoiceRecording(
        original_name=uploaded_file.name,
        mime_type=uploaded_file.content_type,
        size_bytes=uploaded_file.size,
        status='uploaded'
    )
    voice_recording.file.save(uploaded_file.name, uploaded_file)
    
    logger.info(f"Stored voice file: {voice_recording.file.path}, ID: {voice_recording.id}, "
                f"Size: {uploaded_file.size} bytes")
    return voice_recording


def get_audio_duration(file_path: str) -> Optional[int]:
    """
    Get the duration of an audio file in seconds using ffprobe.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Duration in seconds or None if unable to determine
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        elapsed = time.time() - start_time
        
        duration = float(result.stdout.strip())
        logger.info(f"ffprobe duration check completed in {elapsed:.2f}s: {duration:.1f}s total duration")
        return int(duration)
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timeout while checking duration for {file_path}")
        return None
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
        return None


def split_to_segments(voice_path: str, segment_seconds: int = 150) -> List[Dict]:
    """
    Split an audio file into segments using FFmpeg.
    
    Args:
        voice_path: Path to the voice recording file
        segment_seconds: Maximum duration of each segment (default from SEGMENT_SECONDS env)
        
    Returns:
        List of segment metadata dictionaries with keys:
        - path: segment file path
        - start_time: start time in seconds
        - end_time: end time in seconds
        - index: segment index (0-based)
        - ffmpeg_command: exact command used
    """
    segments = []
    temp_dir = tempfile.mkdtemp(prefix='voice_segments_')
    
    try:
        # Get total duration
        duration = get_audio_duration(voice_path)
        if duration is None:
            duration = 300  # Default to 5 minutes if can't determine
            logger.warning(f"Using default duration of {duration}s")
        
        # Calculate number of segments
        num_segments = (duration + segment_seconds - 1) // segment_seconds
        logger.info(f"Splitting {duration}s audio into {num_segments} segments of ≤{segment_seconds}s each")
        
        split_start_time = time.time()
        
        for i in range(num_segments):
            segment_start = time.time()
            start_time = i * segment_seconds
            segment_path = os.path.join(temp_dir, f'segment_{i:03d}.mp3')
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', voice_path,
                '-ss', str(start_time),
                '-t', str(segment_seconds),
                '-acodec', 'mp3',
                '-ar', '16000',  # 16kHz sample rate for Whisper
                '-ac', '1',      # Mono
                '-y',            # Overwrite output
                '-loglevel', 'error',  # Reduce verbosity
                segment_path
            ]
            
            # Log exact command
            cmd_str = ' '.join(cmd)
            logger.info(f"Segment {i+1}/{num_segments} FFmpeg command: {cmd_str}")
            
            # Execute FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error for segment {i}: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
            
            segment_elapsed = time.time() - segment_start
            end_time = min(start_time + segment_seconds, duration)
            
            segment_info = {
                'path': segment_path,
                'start_time': start_time,
                'end_time': end_time,
                'index': i,
                'ffmpeg_command': cmd_str,
                'extraction_time': segment_elapsed
            }
            segments.append(segment_info)
            
            logger.info(f"Created segment {i+1}/{num_segments}: {start_time}s-{end_time}s "
                       f"({segment_elapsed:.2f}s to extract)")
        
        total_split_time = time.time() - split_start_time
        logger.info(f"Audio splitting completed in {total_split_time:.2f}s for {num_segments} segments")
    
    except subprocess.TimeoutExpired as e:
        logger.error(f"FFmpeg timeout during segmentation: {e}")
        # Clean up on error
        cleanup_segments(segments, temp_dir)
        raise
    except Exception as e:
        logger.error(f"Error splitting audio: {e}")
        # Clean up on error
        cleanup_segments(segments, temp_dir)
        raise
    
    return segments


def cleanup_segments(segments: List[Dict], temp_dir: str = None):
    """
    Clean up temporary segment files and directory.
    
    Args:
        segments: List of segment dictionaries
        temp_dir: Temporary directory path
    """
    for segment in segments:
        seg_path = segment.get('path') if isinstance(segment, dict) else segment[0]
        if seg_path and os.path.exists(seg_path):
            try:
                os.remove(seg_path)
                logger.debug(f"Removed segment file: {seg_path}")
            except Exception as e:
                logger.warning(f"Could not remove segment file {seg_path}: {e}")
    
    if temp_dir and os.path.exists(temp_dir):
        try:
            os.rmdir(temp_dir)
            logger.debug(f"Removed temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Could not remove temp directory {temp_dir}: {e}")


def transcribe_segment(
    segment_path: str, 
    segment_index: int = 0,
    prompt: str = WHISPER_PROMPT,
    model: str = None,
    base_url: str = None,
    api_key: str = None,
    retry_count: int = 2
) -> Tuple[str, Dict]:
    """
    Transcribe an audio segment using OpenAI Whisper API.
    
    Args:
        segment_path: Path to the audio segment
        segment_index: Index of the segment (for logging)
        prompt: Guidance prompt for transcription
        model: ASR model name (defaults to settings.ASR_MODEL)
        base_url: OpenAI API base URL (defaults to settings.OPENAI_BASE_URL)
        api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
        retry_count: Number of retries on failure
        
    Returns:
        Tuple of (transcribed_text, metadata_dict) where metadata includes:
        - asr_duration: time taken for ASR
        - retry_attempts: number of retries needed
        - model_used: ASR model name
        - base_url_used: API base URL
    """
    if model is None:
        model = getattr(settings, 'ASR_MODEL', 'whisper-1')
    if base_url is None:
        base_url = getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
    if api_key is None:
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
    
    if not api_key:
        logger.error("OPENAI_API_KEY not configured")
        return "[SEGMENT FAILED]", {'error': 'No API key'}
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    metadata = {
        'model_used': model,
        'base_url_used': base_url,
        'retry_attempts': 0,
        'asr_duration': 0
    }
    
    for attempt in range(retry_count + 1):
        try:
            asr_start = time.time()
            logger.info(f"Starting ASR for segment {segment_index + 1}, attempt {attempt + 1}/{retry_count + 1}")
            
            with open(segment_path, 'rb') as audio_file:
                response = client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    prompt=prompt,
                    language='fa'  # Persian
                )
                
            asr_duration = time.time() - asr_start
            metadata['asr_duration'] = asr_duration
            metadata['retry_attempts'] = attempt
            
            logger.info(f"ASR completed for segment {segment_index + 1} in {asr_duration:.2f}s "
                       f"(attempt {attempt + 1})")
            
            return response.text, metadata
            
        except Exception as e:
            logger.error(f"ASR attempt {attempt + 1} failed for segment {segment_index + 1}: {e}")
            metadata['retry_attempts'] = attempt + 1
            
            if attempt == retry_count:
                metadata['error'] = str(e)
                logger.error(f"All ASR attempts exhausted for segment {segment_index + 1}, inserting failure marker")
                return "[SEGMENT FAILED]", metadata
            
            # Wait before retry (exponential backoff)
            wait_time = 2 ** attempt
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return "[SEGMENT FAILED]", metadata


async def transcribe_segments_concurrent(
    segments: List[Dict],
    prompt: str = WHISPER_PROMPT,
    model: str = None,
    base_url: str = None,
    api_key: str = None,
    max_concurrent: int = MAX_CONCURRENT_ASR
) -> List[Tuple[str, Dict]]:
    """
    Transcribe multiple segments concurrently with rate limiting.
    
    Args:
        segments: List of segment dictionaries
        prompt: Guidance prompt for transcription
        model: ASR model name
        base_url: OpenAI API base URL
        api_key: OpenAI API key
        max_concurrent: Maximum number of concurrent ASR requests (2-3 recommended)
        
    Returns:
        List of (transcript, metadata) tuples in segment order
    """
    logger.info(f"Starting concurrent ASR for {len(segments)} segments with max {max_concurrent} concurrent requests")
    
    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def transcribe_with_semaphore(segment_dict, index):
        async with semaphore:
            # Run in thread pool since OpenAI client is synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                transcribe_segment,
                segment_dict['path'],
                index,
                prompt,
                model,
                base_url,
                api_key,
                2  # retry_count
            )
            return index, result
    
    # Create tasks for all segments
    tasks = [
        transcribe_with_semaphore(segment, i)
        for i, segment in enumerate(segments)
    ]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Sort results by segment index to maintain order
    results.sort(key=lambda x: x[0])
    
    # Extract just the transcripts and metadata
    return [result[1] for result in results]


def merge_transcripts(segments_text: List[str]) -> str:
    """
    Merge multiple transcript segments into a single text.
    
    Args:
        segments_text: List of transcribed text segments
        
    Returns:
        Merged and normalized text
    """
    # Count valid vs failed segments
    failed_count = sum(1 for s in segments_text if "[SEGMENT FAILED]" in s)
    valid_count = len(segments_text) - failed_count
    
    if failed_count > 0:
        logger.warning(f"Merging {valid_count} valid segments and {failed_count} failed segments")
    
    # Join all segments with double newline
    merged = "\n\n".join(segments_text)
    
    # Normalize whitespace
    lines = merged.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Strip whitespace from each line
        line = line.strip()
        if line:  # Keep non-empty lines
            # Normalize multiple spaces to single space
            line = ' '.join(line.split())
            cleaned_lines.append(line)
    
    # Join with single newlines, but preserve paragraph breaks
    result = []
    for i, line in enumerate(cleaned_lines):
        result.append(line)
        # Add extra newline for paragraph breaks (when next line exists)
        if i < len(cleaned_lines) - 1:
            # Check if current line ends with sentence terminator
            if line and line[-1] in '.،؟!':
                # Check if next line starts with capital or is a failed segment marker
                next_line = cleaned_lines[i + 1]
                if next_line.startswith('[') or (next_line and next_line[0].isupper()):
                    result.append('')  # Empty line for paragraph break
    
    final_text = '\n'.join(result)
    
    logger.info(f"Merged {len(segments_text)} segments ({valid_count} valid, {failed_count} failed) "
                f"into {len(final_text)} characters")
    
    return final_text


def persist_note(voice: VoiceRecording, text: str, format: str = 'txt') -> VoiceNote:
    """
    Save transcribed text as a note file and create VoiceNote instance.
    
    Args:
        voice: VoiceRecording instance
        text: Transcribed text content
        format: File format ('txt' or 'md')
        
    Returns:
        VoiceNote instance
    """
    # Generate filename based on voice recording
    base_name = Path(voice.original_name).stem
    note_filename = f"{base_name}_note.{format}"
    
    # Create note content
    content = text.encode('utf-8')
    
    # Create VoiceNote instance
    voice_note = VoiceNote(
        voice=voice,
        format=format,
        size_bytes=len(content)
    )
    
    # Save file
    voice_note.file.save(note_filename, ContentFile(content))
    
    logger.info(f"Created note: {voice_note.file.path}, ID: {voice_note.id}, "
                f"Size: {len(content)} bytes")
    
    return voice_note


def process_voice_recording(voice_id: str) -> Dict:
    """
    Main processing flow for a voice recording with detailed logging.
    
    1. Verify FFmpeg availability
    2. Update status to 'processing'
    3. Split audio into segments
    4. Transcribe each segment (concurrent)
    5. Merge transcripts
    6. Save as note
    7. Update status to 'done' or 'failed'
    
    Args:
        voice_id: UUID of the VoiceRecording to process
        
    Returns:
        Dictionary with processing metadata for hand-off log
    """
    processing_start = time.time()
    handoff_data = {
        'voice_id': voice_id,
        'start_time': processing_start,
        'ffmpeg_available': False,
        'segments': [],
        'asr_model': getattr(settings, 'ASR_MODEL', 'whisper-1'),
        'asr_base_url': getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'segment_seconds': getattr(settings, 'SEGMENT_SECONDS', 150),
        'status': 'failed',
        'error': None
    }
    
    try:
        # Verify FFmpeg availability first
        if not verify_ffmpeg_availability():
            error_msg = "FFmpeg/ffprobe not available. Please install FFmpeg on the system."
            logger.error(error_msg)
            handoff_data['error'] = error_msg
            raise RuntimeError(error_msg)
        
        handoff_data['ffmpeg_available'] = True
        
        # Get voice recording
        voice = VoiceRecording.objects.get(id=voice_id)
        logger.info(f"[START] Processing voice recording: {voice_id}, file: {voice.original_name}")
        
        # Update status to processing
        voice.status = 'processing'
        voice.save()
        
        # Get audio duration
        duration = get_audio_duration(voice.file.path)
        if duration:
            voice.duration_sec = duration
            voice.save()
            handoff_data['total_duration'] = duration
        
        # Split into segments
        segment_seconds = handoff_data['segment_seconds']
        segments = split_to_segments(voice.file.path, segment_seconds=segment_seconds)
        logger.info(f"Split audio into {len(segments)} segments of ≤{segment_seconds}s each")
        
        # Store segment information for hand-off
        handoff_data['segments'] = [
            {
                'index': seg['index'],
                'start_time': seg['start_time'],
                'end_time': seg['end_time'],
                'path': seg['path'],
                'ffmpeg_command': seg['ffmpeg_command'],
                'extraction_time': seg.get('extraction_time', 0)
            }
            for seg in segments
        ]
        
        # Transcribe segments concurrently
        asr_start = time.time()
        
        # Run async transcription in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            transcription_results = loop.run_until_complete(
                transcribe_segments_concurrent(
                    segments,
                    prompt=WHISPER_PROMPT,
                    model=handoff_data['asr_model'],
                    base_url=handoff_data['asr_base_url'],
                    api_key=getattr(settings, 'OPENAI_API_KEY', None),
                    max_concurrent=min(3, len(segments))  # Max 3 concurrent
                )
            )
        finally:
            loop.close()
        
        asr_total_time = time.time() - asr_start
        
        # Extract transcripts and metadata
        transcripts = []
        for i, (text, metadata) in enumerate(transcription_results):
            transcripts.append(text)
            # Add ASR metadata to segment info
            handoff_data['segments'][i]['asr_duration'] = metadata.get('asr_duration', 0)
            handoff_data['segments'][i]['retry_attempts'] = metadata.get('retry_attempts', 0)
            if '[SEGMENT FAILED]' in text:
                handoff_data['segments'][i]['failed'] = True
                logger.warning(f"Segment {i+1} failed after {metadata.get('retry_attempts', 0)} retries")
        
        logger.info(f"ASR completed for all {len(segments)} segments in {asr_total_time:.2f}s total")
        
        # Clean up segment files
        cleanup_segments(segments, os.path.dirname(segments[0]['path']) if segments else None)
        
        # Merge transcripts
        merged_text = merge_transcripts(transcripts)
        handoff_data['merged_text_length'] = len(merged_text)
        
        # Count failed segments
        failed_segments = sum(1 for t in transcripts if '[SEGMENT FAILED]' in t)
        if failed_segments > 0:
            handoff_data['failed_segments'] = failed_segments
            logger.warning(f"Note contains {failed_segments} failed segment markers")
        
        # Save as note
        note = persist_note(voice, merged_text)
        handoff_data['note_path'] = note.file.path
        handoff_data['note_size'] = note.size_bytes
        handoff_data['note_id'] = str(note.id)
        
        # Update status to done
        voice.status = 'done'
        voice.save()
        handoff_data['status'] = 'done'
        
        # Calculate total processing time
        total_time = time.time() - processing_start
        handoff_data['total_processing_time'] = total_time
        
        logger.info(f"[END] Successfully processed voice recording {voice_id} in {total_time:.2f}s total")
        logger.info(f"Output: {note.file.path} ({note.size_bytes} bytes)")
        
    except VoiceRecording.DoesNotExist:
        error_msg = f"Voice recording not found: {voice_id}"
        logger.error(error_msg)
        handoff_data['error'] = error_msg
        raise
    
    except Exception as e:
        error_msg = f"Error processing voice recording {voice_id}: {e}"
        logger.error(error_msg, exc_info=True)
        handoff_data['error'] = str(e)
        
        # Update status to failed
        try:
            voice = VoiceRecording.objects.get(id=voice_id)
            voice.status = 'failed'
            voice.save()
        except:
            pass
        
        raise
    
    finally:
        handoff_data['end_time'] = time.time()
        # Log hand-off data
        logger.info(f"Hand-off data: {handoff_data}")
    
    return handoff_data