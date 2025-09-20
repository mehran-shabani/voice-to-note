"""
DRF API tests for voice upload endpoint validating happy and error paths.

These tests mock FFmpeg and ASR for speed and determinism.
"""
from unittest.mock import patch
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from records.models import VoiceRecording, VoiceNote


class VoiceUploadAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('records:upload_voice')

    def _make_audio(self, name='test.wav', content=b'abc', content_type='audio/wav', size=None):
        if size is not None:
            content = b'x' * size
        return SimpleUploadedFile(name, content, content_type=content_type)

    @patch('records.services.verify_ffmpeg_availability', return_value=True)
    @patch('records.services.transcribe_segment')
    @patch('records.services.split_to_segments')
    @patch('records.services.get_audio_duration')
    def test_happy_path_201_created_and_location_and_note(
        self,
        mock_duration,
        mock_split,
        mock_transcribe,
        mock_ffmpeg,
    ):
        """5-min flow: upload → split → ASR → merge → status=done; returns 201 + Location."""
        # 5 minutes
        mock_duration.return_value = 300
        mock_split.return_value = [
            {
                'path': '/tmp/segment_000.mp3',
                'start_time': 0,
                'end_time': 150,
                'index': 0,
                'ffmpeg_command': 'ffmpeg ...',
                'extraction_time': 0.01,
            },
            {
                'path': '/tmp/segment_001.mp3',
                'start_time': 150,
                'end_time': 300,
                'index': 1,
                'ffmpeg_command': 'ffmpeg ...',
                'extraction_time': 0.01,
            },
        ]
        mock_transcribe.side_effect = [
            ("segment one text", {'asr_duration': 0.02, 'retry_attempts': 0}),
            ("segment two text", {'asr_duration': 0.03, 'retry_attempts': 0}),
        ]

        audio_file = self._make_audio()

        with patch('os.remove'), patch('os.rmdir'):
            response = self.client.post(self.url, {'audio': audio_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.has_header('Location'))
        # DB artifacts
        self.assertEqual(VoiceRecording.objects.count(), 1)
        voice = VoiceRecording.objects.first()
        self.assertEqual(voice.status, 'done')
        self.assertEqual(voice.duration_sec, 300)
        self.assertEqual(VoiceNote.objects.filter(voice=voice).count(), 1)
        note = VoiceNote.objects.get(voice=voice)
        self.assertTrue(note.file.path.endswith('.txt'))
        # Ensure merged note content was written
        with open(note.file.path, 'rb') as fh:
            body = fh.read().decode('utf-8', errors='ignore')
        self.assertIn('segment one text', body)
        self.assertIn('segment two text', body)

    def test_invalid_mime_400(self):
        audio_file = self._make_audio(name='bad.txt', content_type='text/plain')
        response = self.client.post(self.url, {'audio': audio_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get('error'), 'INVALID_MIME')

    def test_oversize_413(self):
        # 31MB
        audio_file = self._make_audio(size=31 * 1024 * 1024)
        response = self.client.post(self.url, {'audio': audio_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(response.json().get('error'), 'TOO_LARGE')

    @patch('records.services.verify_ffmpeg_availability', return_value=True)
    @patch('records.services.transcribe_segment')
    @patch('records.services.split_to_segments')
    @patch('records.services.get_audio_duration')
    def test_asr_failure_inserts_segment_failed_marker(
        self,
        mock_duration,
        mock_split,
        mock_transcribe,
        mock_ffmpeg,
    ):
        """ASR failures after retries result in [SEGMENT FAILED] included in merged note."""
        mock_duration.return_value = 120
        mock_split.return_value = [
            {
                'path': '/tmp/segment_000.mp3',
                'start_time': 0,
                'end_time': 60,
                'index': 0,
                'ffmpeg_command': 'ffmpeg ...',
                'extraction_time': 0.01,
            },
            {
                'path': '/tmp/segment_001.mp3',
                'start_time': 60,
                'end_time': 120,
                'index': 1,
                'ffmpeg_command': 'ffmpeg ...',
                'extraction_time': 0.01,
            },
        ]
        mock_transcribe.side_effect = [
            ("ok text", {'asr_duration': 0.02, 'retry_attempts': 0}),
            ("[SEGMENT FAILED]", {'asr_duration': 0.04, 'retry_attempts': 2}),
        ]

        audio_file = self._make_audio()

        with patch('os.remove'), patch('os.rmdir'):
            response = self.client.post(self.url, {'audio': audio_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        voice = VoiceRecording.objects.first()
        note = VoiceNote.objects.get(voice=voice)
        with open(note.file.path, 'rb') as fh:
            body = fh.read().decode('utf-8', errors='ignore')
        self.assertIn('[SEGMENT FAILED]', body)

    @patch('records.services.verify_ffmpeg_availability', return_value=True)
    @patch('records.services.transcribe_segment')
    @patch('records.services.split_to_segments')
    @patch('records.services.get_audio_duration')
    def test_handoff_data_contains_per_segment_timings(
        self,
        mock_duration,
        mock_split,
        mock_transcribe,
        mock_ffmpeg,
    ):
        """Service returns per-segment asr_duration in handoff_data for logging/QA."""
        from records.services import process_voice_recording, store_voice_file

        mock_duration.return_value = 10
        mock_split.return_value = [
            {
                'path': '/tmp/segment_000.mp3',
                'start_time': 0,
                'end_time': 10,
                'index': 0,
                'ffmpeg_command': 'ffmpeg ...',
                'extraction_time': 0.01,
            }
        ]
        mock_transcribe.return_value = ("ok", {'asr_duration': 0.05, 'retry_attempts': 1})

        audio_file = self._make_audio()
        voice = store_voice_file(audio_file)

        with patch('os.remove'), patch('os.rmdir'):
            handoff = process_voice_recording(str(voice.id))

        self.assertEqual(handoff['status'], 'done')
        self.assertIn('segments', handoff)
        self.assertIn('asr_duration', handoff['segments'][0])
        self.assertIn('retry_attempts', handoff['segments'][0])
