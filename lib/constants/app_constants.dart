class AppConstants {
  // App Settings
  static const String appName = 'VoiceNote';
  static const int maxRecordingMinutes = 5;
  static const int maxRecordingSeconds = maxRecordingMinutes * 60;
  
  // Audio Settings
  static const String audioContainer = 'm4a';
  static const String audioCodec = 'aac';
  static const int audioBitrateKbps = 64;
  static const int audioBitrate = audioBitrateKbps * 1000; // Convert to bps
  
  // File naming
  static const String filePrefix = 'voicenote';
  static const String editedSuffix = '_edited';
  
  // Network Settings  
  static const String uploadEndpoint = 'https://your-server.com/api/voices/';
  static const Duration uploadTimeout = Duration(seconds: 60);
  
  // Storage
  static const String recordingsDirectory = 'recordings';
  static const String tempDirectory = 'temp';
  static const String snapshotsDirectory = 'snapshots';
}