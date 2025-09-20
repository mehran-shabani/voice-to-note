# VoiceNote - Flutter Android App

A Flutter Android application for recording, editing, and uploading voice notes with AAC audio compression.

## Features

- **Recording**: Record audio in M4A format with AAC codec at 64kbps
- **Pause/Resume**: Pause and resume recording without creating multiple files
- **Auto-stop**: Automatically stops recording at 5 minutes
- **Lightweight Editor**: Cut audio segments with single-level undo
- **Upload**: Upload recordings via multipart/form-data to backend server
- **Non-destructive Editing**: Original recordings are preserved

## Quick Start

### Prerequisites

- Flutter SDK 3.0+
- Android Studio or VS Code with Flutter plugins
- Android device or emulator (API 21+)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   flutter pub get
   ```

3. Configure the upload endpoint in `/lib/constants/app_constants.dart`:
   ```dart
   static const String uploadEndpoint = 'https://your-server.com/api/voices/';
   ```

4. Run the app:
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── constants/          # App constants and configuration
├── models/            # Data models
├── recording/         # Recording service and providers
├── editor/           # Audio editing functionality
├── upload/           # File upload service
├── screens/          # Main app screens
└── widgets/          # Reusable UI components

docs/
├── qa_checklist.md   # Manual testing checklist
└── handoff_log.md    # Implementation details and decisions
```

## Key Components

### Recording Service
- Uses `record` package for AAC audio recording
- Saves to app-scoped storage
- Automatic 5-minute limit

### Editor Service
- FFmpeg-based audio manipulation
- Non-destructive cut operations
- Snapshot-based undo system

### Upload Service
- Dio HTTP client with 60-second timeout
- Multipart/form-data uploads
- Progress tracking

## Testing

See `/docs/qa_checklist.md` for comprehensive manual testing procedures.

## Building for Release

```bash
flutter build apk --release
```

The APK will be available at `build/app/outputs/flutter-apk/app-release.apk`

## License

This project follows the specifications in `agent.md`.