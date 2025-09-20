# VoiceNote Flutter App - Hand-off Log

## Implementation Summary
Date: September 20, 2025
Agent: Flutter Android Frontend (Recorder + Minimal Editor + Uploader)

## Key Decisions & Constants

### Audio Configuration
- **Container**: M4A (MPEG-4 Audio)
- **Codec**: AAC-LC (Low Complexity)
- **Bitrate**: 64 kbps
- **Sample Rate**: 44.1 kHz
- **Channels**: Mono (1 channel)
- **Max Duration**: 5 minutes (300 seconds)
- **Estimated File Size**: ~4MB per minute, ~20MB for 5 minutes

### File Naming Convention
- **Recording Files**: `voicenote_YYYY-MM-DD_HH-mm-ss.m4a`
- **Edited Files**: `voicenote_YYYY-MM-DD_HH-mm-ss_edited.m4a`
- **Snapshot Files**: `snapshot_YYYYMMDD_HHmmss.m4a` (temporary, for undo)

### Storage Locations
- **App Scoped Storage**: `/Android/data/com.example.voicenote/files/`
- **Recordings**: `{app_storage}/recordings/`
- **Snapshots**: `{app_storage}/snapshots/` (temporary)
- **Temp Files**: `{app_storage}/temp/` (temporary during editing)

## Plugin Versions Used

```yaml
dependencies:
  flutter_riverpod: ^2.4.9        # State management
  record: ^5.0.4                  # Audio recording
  ffmpeg_kit_flutter_audio: ^6.0.3 # Audio manipulation
  path_provider: ^2.1.1          # File system access
  path: ^1.8.3                   # Path manipulation
  permission_handler: ^11.1.0    # Runtime permissions
  dio: ^5.4.0                    # HTTP networking
  intl: ^0.18.1                  # Date formatting
  uuid: ^4.2.2                   # Unique ID generation
  just_audio: ^0.9.36            # Audio duration detection
```

## Architecture Decisions

### State Management
- **Riverpod** chosen for its simplicity and type safety
- Minimal state with three main providers:
  - `recordingServiceProvider`: Manages recording state
  - `editorStateProvider`: Manages editing state
  - `uploadServiceProvider`: Handles file uploads

### Service Layer Pattern
- Separate service classes for recording, editing, and uploading
- Services handle business logic and file operations
- Providers wrap services for state management
- UI components consume providers

### Non-Destructive Editing
- Original files are never modified
- Snapshots created before each edit operation
- Single-level undo via snapshot restoration
- Edited files saved with new names

## Sample File Paths

### Recording Output
```
/data/data/com.example.voicenote/files/recordings/voicenote_2025-09-20_14-30-45.m4a
```

### Edited File Output
```
/data/data/com.example.voicenote/files/recordings/voicenote_2025-09-20_14-35-12_edited.m4a
```

### Temporary Snapshot (deleted after save/undo)
```
/data/data/com.example.voicenote/files/snapshots/snapshot_20250920_143515.m4a
```

## Sample Upload Request

### Request Format
```http
POST /api/voices/ HTTP/1.1
Host: your-server.com
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="audio"; filename="voicenote_2025-09-20_14-30-45.m4a"
Content-Type: audio/mp4

[Binary M4A data]
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

### Field Details
- **Field Name**: `audio` (required by backend)
- **Content-Type**: `audio/mp4` (M4A files use this MIME type)
- **Timeout**: 60 seconds

## API Response Handling

### Success Responses Accepted
1. **201 Created** (Preferred)
   - Empty body expected
   - Optional `Location` header with resource URL
   
2. **200 OK** (Also accepted)
   - Body ignored
   - Treated as successful upload

### Error Responses Handled
- **400 Bad Request**: Invalid MIME type
- **413 Payload Too Large**: File exceeds size limit
- **500 Internal Server Error**: Processing error
- **Network errors**: Connection timeout, no connection

## Implementation Notes

### FFmpeg Integration
- Using `ffmpeg_kit_flutter_audio` package for audio manipulation
- Cut operations use FFmpeg to extract and concatenate segments
- Maintains original codec settings (AAC @ 64kbps)

### Permission Handling
- Microphone permission requested at recording start
- Graceful handling if permission denied
- No external storage permissions needed (app-scoped storage)

### Memory Management
- Audio files streamed during upload (not loaded into memory)
- Temporary files cleaned up after operations
- Snapshots deleted after undo or save

## Known Limitations & TODOs for Backend Agent

### Current Limitations
1. **Android Only**: iOS support not implemented
2. **No Waveform Visualization**: Audio selection is time-based only
3. **No Audio Preview**: Cannot play audio in editor
4. **Single Undo Level**: Only one undo operation available
5. **Fixed Recording Limit**: Hard-coded 5-minute maximum
6. **No Chunked Upload**: Single request for entire file

### Backend Requirements
1. **Endpoint**: Must accept `POST /api/voices/`
2. **Field Name**: Must accept `audio` field in multipart/form-data
3. **File Types**: Should accept `audio/mp4`, `audio/m4a`, `audio/aac`
4. **Size Limit**: Should handle files up to ~25MB
5. **Response**: Should return 201 Created (preferred) or 200 OK
6. **Timeout**: Should process within 60 seconds

### Suggested Backend Improvements
1. Return processing status in response body (optional)
2. Include transcription ID in Location header
3. Implement progress webhook for long processing
4. Support resumable uploads for poor connections

## Testing Recommendations

### Critical Test Scenarios
1. **5-minute recording**: Verify auto-stop and file size (~20MB)
2. **Multiple cuts**: Test undo functionality with 2-3 cuts
3. **Upload interruption**: Test cancel and retry behavior
4. **Permission denial**: Test graceful degradation
5. **Low storage**: Test error handling with <50MB free space

### Performance Benchmarks
- Recording start: < 500ms
- Cut operation: < 2 seconds for 5-minute file
- Upload progress: Updates every 100ms
- File save: < 1 second

## Deployment Checklist

Before deploying to production:
1. [ ] Update `UPLOAD_ENDPOINT` in constants to production server
2. [ ] Set proper app bundle ID for production
3. [ ] Configure ProGuard rules for release build
4. [ ] Test on minimum SDK version (API 21)
5. [ ] Verify server CORS settings allow app origin
6. [ ] Set up crash reporting (Firebase Crashlytics recommended)
7. [ ] Configure proper app signing for Play Store

## Contact & Support

For questions about this implementation:
- Review `/workspace/agent.md` for requirements
- Check `/workspace/docs/qa_checklist.md` for testing procedures
- All code follows Flutter best practices and is fully documented

---
End of Hand-off Log