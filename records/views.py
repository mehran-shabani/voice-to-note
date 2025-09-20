"""
API views for voice recording upload and processing.
"""
import logging
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from .services import store_voice_file, process_voice_recording

logger = logging.getLogger(__name__)

# Accepted MIME types for audio files
ACCEPTED_MIME_TYPES = {
    'audio/m4a',
    'audio/mp4',
    'audio/aac',
    'audio/ogg',
    'audio/wav',
    'audio/x-m4a',  # Some browsers send this
    'audio/mpeg',   # Sometimes m4a is detected as this
}

# Maximum file size (30MB)
MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB in bytes


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint.
    Returns: {"status": "ok"}
    """
    return JsonResponse({"status": "ok"})


@api_view(['POST'])
@parser_classes([MultiPartParser])
def upload_voice(request):
    """
    Upload a voice recording and trigger processing.
    
    Expected:
    - multipart/form-data with 'audio' field containing the file
    - MIME type in accepted list
    - File size <= 30MB
    
    Returns:
    - 201 Created with Location header and empty body (preferred)
    - 200 OK in minimal mode
    - 400 INVALID_MIME if MIME type not accepted
    - 413 TOO_LARGE if file size exceeds limit
    - 500 PROCESSING_ERROR if processing fails
    """
    try:
        # Check if audio file is present
        if 'audio' not in request.FILES:
            logger.error("No audio file provided in request")
            return Response(
                {"error": "No audio file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        audio_file = request.FILES['audio']
        
        # Log receipt of file
        logger.info(f"Received audio file: {audio_file.name}, "
                   f"size: {audio_file.size} bytes, "
                   f"content_type: {audio_file.content_type}")
        
        # Validate MIME type
        if audio_file.content_type not in ACCEPTED_MIME_TYPES:
            logger.error(f"Invalid MIME type: {audio_file.content_type}")
            return Response(
                {"error": "INVALID_MIME", 
                 "message": f"MIME type {audio_file.content_type} not accepted. "
                           f"Accepted types: {', '.join(ACCEPTED_MIME_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size
        if audio_file.size > MAX_FILE_SIZE:
            logger.error(f"File too large: {audio_file.size} bytes")
            return Response(
                {"error": "TOO_LARGE",
                 "message": f"File size {audio_file.size} exceeds maximum of {MAX_FILE_SIZE} bytes"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Store the file
        voice_recording = store_voice_file(audio_file)
        logger.info(f"Stored voice recording with ID: {voice_recording.id}")
        
        # Trigger processing (synchronous for now)
        try:
            process_voice_recording(str(voice_recording.id))
            logger.info(f"Successfully processed voice recording: {voice_recording.id}")
        except Exception as e:
            logger.error(f"Processing failed for {voice_recording.id}: {e}", exc_info=True)
            # Set status to failed (already done in service, but ensure it)
            voice_recording.status = 'failed'
            voice_recording.save()
            
            return Response(
                {"error": "PROCESSING_ERROR",
                 "message": "Failed to process audio file"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Return 201 Created with Location header (preferred)
        response = Response(status=status.HTTP_201_CREATED)
        response['Location'] = f'/api/voices/{voice_recording.id}'
        
        logger.info(f"Returning 201 Created for voice recording: {voice_recording.id}")
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error in upload_voice: {e}", exc_info=True)
        return Response(
            {"error": "PROCESSING_ERROR",
             "message": "An unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )