"""
Unit tests for voice recording upload API.
"""
import os
import tempfile
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from .models import VoiceRecording, VoiceNote


class HealthCheckTestCase(TestCase):
    """Test cases for health check endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('health_check')
    
    def test_health_check_returns_ok(self):
        """Test that health check returns status ok."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class UploadVoiceTestCase(TestCase):
    """Test cases for voice upload endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('records:upload_voice')
    
    def create_test_audio_file(self, filename='test.m4a', content=b'fake audio content', 
                               content_type='audio/m4a', size=None):
        """Helper to create a test audio file."""
        if size is not None:
            content = b'x' * size
        return SimpleUploadedFile(filename, content, content_type=content_type)
    
    @patch('records.views.process_voice_recording')
    @patch('records.services.VoiceRecording.save')
    def test_successful_upload_returns_201(self, mock_save, mock_process):
        """Test successful upload returns 201 Created with Location header."""
        # Create a mock for the saved voice recording
        mock_voice = MagicMock()
        mock_voice.id = 'test-uuid-123'
        
        with patch('records.views.store_voice_file', return_value=mock_voice):
            audio_file = self.create_test_audio_file()
            response = self.client.post(
                self.url,
                {'audio': audio_file},
                format='multipart'
            )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('Location', response)
        self.assertEqual(response['Location'], '/api/voices/test-uuid-123')
        self.assertEqual(response.content, b'')  # Empty body
        mock_process.assert_called_once_with('test-uuid-123')
    
    def test_missing_audio_file_returns_400(self):
        """Test that missing audio file returns 400 Bad Request."""
        response = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_invalid_mime_type_returns_400(self):
        """Test that invalid MIME type returns 400 INVALID_MIME."""
        audio_file = self.create_test_audio_file(
            filename='test.txt',
            content_type='text/plain'
        )
        response = self.client.post(
            self.url,
            {'audio': audio_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()
        self.assertEqual(response_data['error'], 'INVALID_MIME')
    
    def test_file_too_large_returns_413(self):
        """Test that file exceeding size limit returns 413 TOO_LARGE."""
        # Create a file larger than 30MB
        large_size = 31 * 1024 * 1024  # 31MB
        audio_file = self.create_test_audio_file(size=large_size)
        
        response = self.client.post(
            self.url,
            {'audio': audio_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        response_data = response.json()
        self.assertEqual(response_data['error'], 'TOO_LARGE')
    
    @patch('records.views.process_voice_recording')
    def test_processing_error_returns_500(self, mock_process):
        """Test that processing error returns 500 PROCESSING_ERROR."""
        # Make process_voice_recording raise an exception
        mock_process.side_effect = Exception("Processing failed")
        
        mock_voice = MagicMock()
        mock_voice.id = 'test-uuid-456'
        mock_voice.status = 'uploaded'
        
        with patch('records.views.store_voice_file', return_value=mock_voice):
            audio_file = self.create_test_audio_file()
            response = self.client.post(
                self.url,
                {'audio': audio_file},
                format='multipart'
            )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        response_data = response.json()
        self.assertEqual(response_data['error'], 'PROCESSING_ERROR')
        mock_voice.save.assert_called()  # Should save with failed status
        self.assertEqual(mock_voice.status, 'failed')
    
    def test_accepted_mime_types(self):
        """Test that all accepted MIME types are handled correctly."""
        accepted_types = [
            ('audio/m4a', 'test.m4a'),
            ('audio/mp4', 'test.mp4'),
            ('audio/aac', 'test.aac'),
            ('audio/ogg', 'test.ogg'),
            ('audio/wav', 'test.wav'),
        ]
        
        for content_type, filename in accepted_types:
            with patch('records.views.store_voice_file') as mock_store:
                with patch('records.views.process_voice_recording'):
                    mock_voice = MagicMock()
                    mock_voice.id = f'test-{filename}'
                    mock_store.return_value = mock_voice
                    
                    audio_file = self.create_test_audio_file(
                        filename=filename,
                        content_type=content_type
                    )
                    response = self.client.post(
                        self.url,
                        {'audio': audio_file},
                        format='multipart'
                    )
                    
                    self.assertEqual(
                        response.status_code, 
                        status.HTTP_201_CREATED,
                        f"Failed for {content_type}"
                    )


class ServiceFunctionsTestCase(TestCase):
    """Test cases for service functions."""
    
    def test_store_voice_file_creates_record(self):
        """Test that store_voice_file creates a VoiceRecording."""
        from records.services import store_voice_file
        
        # Create a mock uploaded file
        uploaded_file = SimpleUploadedFile(
            'test_audio.m4a',
            b'fake audio content',
            content_type='audio/m4a'
        )
        
        # Store the file
        voice_recording = store_voice_file(uploaded_file)
        
        # Verify the record was created
        self.assertIsNotNone(voice_recording.id)
        self.assertEqual(voice_recording.original_name, 'test_audio.m4a')
        self.assertEqual(voice_recording.mime_type, 'audio/m4a')
        self.assertEqual(voice_recording.size_bytes, len(b'fake audio content'))
        self.assertEqual(voice_recording.status, 'uploaded')
        self.assertTrue(voice_recording.file)
    
    @patch('subprocess.run')
    def test_get_audio_duration(self, mock_run):
        """Test that get_audio_duration returns correct duration."""
        from records.services import get_audio_duration
        
        # Mock ffprobe output
        mock_run.return_value = MagicMock(
            stdout='300.5\n',
            returncode=0
        )
        
        duration = get_audio_duration('/fake/path/audio.m4a')
        self.assertEqual(duration, 300)
    
    def test_merge_transcripts(self):
        """Test that merge_transcripts correctly merges text segments."""
        from records.services import merge_transcripts
        
        segments = [
            "This is the first segment.",
            "This is the second segment.",
            "[SEGMENT FAILED]",
            "This is the fourth segment."
        ]
        
        merged = merge_transcripts(segments)
        
        # Should join segments with double newlines and include failed marker
        self.assertIn("This is the first segment", merged)
        self.assertIn("This is the second segment", merged)
        self.assertIn("[SEGMENT FAILED]", merged)
        self.assertIn("This is the fourth segment", merged)
    
    @patch('records.services.transcribe_segment')
    @patch('records.services.split_to_segments')
    @patch('records.services.get_audio_duration')
    def test_process_voice_recording_success(self, mock_duration, mock_split, mock_transcribe):
        """Test successful processing of voice recording."""
        from records.services import process_voice_recording, store_voice_file
        
        # Create a voice recording
        uploaded_file = SimpleUploadedFile(
            'test_audio.m4a',
            b'fake audio content',
            content_type='audio/m4a'
        )
        voice_recording = store_voice_file(uploaded_file)
        
        # Mock dependencies
        mock_duration.return_value = 150
        mock_split.return_value = [
            ('/tmp/segment_000.mp3', 0, 150)
        ]
        mock_transcribe.return_value = "This is the transcribed text."
        
        # Mock file cleanup
        with patch('os.remove'):
            with patch('os.rmdir'):
                # Process the recording
                process_voice_recording(str(voice_recording.id))
        
        # Reload from database
        voice_recording.refresh_from_db()
        
        # Verify status is done
        self.assertEqual(voice_recording.status, 'done')
        self.assertEqual(voice_recording.duration_sec, 150)
        
        # Verify note was created
        notes = VoiceNote.objects.filter(voice=voice_recording)
        self.assertEqual(notes.count(), 1)
        note = notes.first()
        self.assertEqual(note.format, 'txt')
    
    @patch('records.services.transcribe_segment')
    def test_process_voice_recording_failure(self, mock_transcribe):
        """Test that processing failure updates status to failed."""
        from records.services import process_voice_recording, store_voice_file
        
        # Create a voice recording
        uploaded_file = SimpleUploadedFile(
            'test_audio.m4a',
            b'fake audio content',
            content_type='audio/m4a'
        )
        voice_recording = store_voice_file(uploaded_file)
        
        # Make transcribe fail
        mock_transcribe.side_effect = Exception("Transcription failed")
        
        # Process should raise exception
        with self.assertRaises(Exception):
            process_voice_recording(str(voice_recording.id))
        
        # Reload from database
        voice_recording.refresh_from_db()
        
        # Verify status is failed
        self.assertEqual(voice_recording.status, 'failed')