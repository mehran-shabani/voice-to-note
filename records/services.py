"""
Service functions for processing voice recordings.
"""
import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI
from .models import VoiceRecording, VoiceNote

logger = logging.getLogger(__name__)

# Persian guidance prompt for Whisper ASR
WHISPER_PROMPT = """متن این فایل صوتی مربوط به یک جلسهٔ آموزشی به زبان فارسی است.
لطفاً واژگان را با املای رایج فارسی بنویس و اعداد را به صورت رقم ثبت کن.
نام‌های علمی و اصطلاحات را همان‌گونه که ادا می‌شود ثبت کن.
از حدس‌زدن یا افزودن کلمات خودداری کن؛ فقط آنچه گفته می‌شود را بنویس."""


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
    
    logger.info(f"Stored voice file: {voice_recording.file.path}, ID: {voice_recording.id}")
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return int(duration)
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
        return None


def split_to_segments(voice_path: str, segment_seconds: int = 150) -> List[Tuple[str, int, int]]:
    """
    Split an audio file into segments using FFmpeg.
    
    Args:
        voice_path: Path to the voice recording file
        segment_seconds: Maximum duration of each segment
        
    Returns:
        List of tuples (segment_path, start_time, end_time)
    """
    segments = []
    temp_dir = tempfile.mkdtemp(prefix='voice_segments_')
    
    try:
        # Get total duration
        duration = get_audio_duration(voice_path)
        if duration is None:
            duration = 300  # Default to 5 minutes if can't determine
        
        # Calculate number of segments
        num_segments = (duration + segment_seconds - 1) // segment_seconds
        
        for i in range(num_segments):
            start_time = i * segment_seconds
            segment_path = os.path.join(temp_dir, f'segment_{i:03d}.mp3')
            
            # Use FFmpeg to extract segment
            cmd = [
                'ffmpeg',
                '-i', voice_path,
                '-ss', str(start_time),
                '-t', str(segment_seconds),
                '-acodec', 'mp3',
                '-ar', '16000',  # 16kHz sample rate for Whisper
                '-ac', '1',      # Mono
                '-y',            # Overwrite output
                segment_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            end_time = min(start_time + segment_seconds, duration)
            segments.append((segment_path, start_time, end_time))
            
            logger.info(f"Created segment {i+1}/{num_segments}: {start_time}s-{end_time}s")
    
    except Exception as e:
        logger.error(f"Error splitting audio: {e}")
        # Clean up on error
        for seg_path, _, _ in segments:
            if os.path.exists(seg_path):
                os.remove(seg_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        raise
    
    return segments


def transcribe_segment(
    segment_path: str, 
    prompt: str = WHISPER_PROMPT,
    model: str = None,
    base_url: str = None,
    api_key: str = None,
    retry_count: int = 2
) -> str:
    """
    Transcribe an audio segment using OpenAI Whisper API.
    
    Args:
        segment_path: Path to the audio segment
        prompt: Guidance prompt for transcription
        model: ASR model name (defaults to settings.ASR_MODEL)
        base_url: OpenAI API base URL (defaults to settings.OPENAI_BASE_URL)
        api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
        retry_count: Number of retries on failure
        
    Returns:
        Transcribed text or '[SEGMENT FAILED]' on error
    """
    if model is None:
        model = settings.ASR_MODEL
    if base_url is None:
        base_url = settings.OPENAI_BASE_URL
    if api_key is None:
        api_key = settings.OPENAI_API_KEY
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    for attempt in range(retry_count + 1):
        try:
            with open(segment_path, 'rb') as audio_file:
                response = client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    prompt=prompt,
                    language='fa'  # Persian
                )
                return response.text
        except Exception as e:
            logger.error(f"Transcription attempt {attempt + 1} failed: {e}")
            if attempt == retry_count:
                return "[SEGMENT FAILED]"
    
    return "[SEGMENT FAILED]"


def merge_transcripts(segments_text: List[str]) -> str:
    """
    Merge multiple transcript segments into a single text.
    
    Args:
        segments_text: List of transcribed text segments
        
    Returns:
        Merged and normalized text
    """
    # Filter out failed segments markers for counting
    valid_segments = [s for s in segments_text if s != "[SEGMENT FAILED]"]
    
    # Join all segments with double newline
    merged = "\n\n".join(segments_text)
    
    # Normalize whitespace
    lines = merged.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Strip whitespace from each line
        line = line.strip()
        if line:  # Keep non-empty lines
            cleaned_lines.append(line)
    
    # Join with single newlines, but preserve paragraph breaks
    result = []
    for i, line in enumerate(cleaned_lines):
        result.append(line)
        # Add extra newline for paragraph breaks (when next line exists and isn't continuation)
        if i < len(cleaned_lines) - 1 and not line.endswith(('.', '،', '؟', '!')):
            if cleaned_lines[i + 1] and cleaned_lines[i + 1][0].isupper():
                result.append('')  # Empty line for paragraph break
    
    final_text = '\n'.join(result)
    
    logger.info(f"Merged {len(valid_segments)} valid segments into {len(final_text)} characters")
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
    
    logger.info(f"Created note: {voice_note.file.path}, ID: {voice_note.id}")
    return voice_note


def process_voice_recording(voice_id: str):
    """
    Main processing flow for a voice recording.
    
    1. Update status to 'processing'
    2. Split audio into segments
    3. Transcribe each segment
    4. Merge transcripts
    5. Save as note
    6. Update status to 'done' or 'failed'
    
    Args:
        voice_id: UUID of the VoiceRecording to process
    """
    try:
        # Get voice recording
        voice = VoiceRecording.objects.get(id=voice_id)
        logger.info(f"Starting processing for voice recording: {voice_id}")
        
        # Update status to processing
        voice.status = 'processing'
        voice.save()
        
        # Get audio duration
        duration = get_audio_duration(voice.file.path)
        if duration:
            voice.duration_sec = duration
            voice.save()
        
        # Split into segments
        segments = split_to_segments(
            voice.file.path, 
            segment_seconds=settings.SEGMENT_SECONDS
        )
        logger.info(f"Split audio into {len(segments)} segments")
        
        # Transcribe each segment
        transcripts = []
        for i, (segment_path, start_time, end_time) in enumerate(segments):
            logger.info(f"Transcribing segment {i+1}/{len(segments)}: {start_time}s-{end_time}s")
            text = transcribe_segment(segment_path)
            transcripts.append(text)
        
        # Clean up segment files
        for segment_path, _, _ in segments:
            try:
                os.remove(segment_path)
            except Exception as e:
                logger.warning(f"Could not remove segment file: {e}")
        
        # Clean up temp directory
        if segments:
            temp_dir = os.path.dirname(segments[0][0])
            try:
                os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(f"Could not remove temp directory: {e}")
        
        # Merge transcripts
        merged_text = merge_transcripts(transcripts)
        
        # Save as note
        note = persist_note(voice, merged_text)
        
        # Update status to done
        voice.status = 'done'
        voice.save()
        
        logger.info(f"Successfully processed voice recording: {voice_id}")
        
    except VoiceRecording.DoesNotExist:
        logger.error(f"Voice recording not found: {voice_id}")
        raise
    
    except Exception as e:
        logger.error(f"Error processing voice recording {voice_id}: {e}", exc_info=True)
        
        # Update status to failed
        try:
            voice = VoiceRecording.objects.get(id=voice_id)
            voice.status = 'failed'
            voice.save()
        except:
            pass
        
        raise