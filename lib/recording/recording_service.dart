import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:intl/intl.dart';
import 'package:voicenote/constants/app_constants.dart';
import 'package:voicenote/models/recording_meta.dart';

class RecordingService {
  final AudioRecorder _recorder = AudioRecorder();
  Timer? _durationTimer;
  Timer? _autoStopTimer;
  
  final ValueNotifier<Duration> recordingDuration = ValueNotifier(Duration.zero);
  final ValueNotifier<RecordingState> recordingState = ValueNotifier(RecordingState.idle);
  
  RecordingMeta? _currentRecording;
  String? _currentFilePath;
  DateTime? _recordingStartTime;

  Future<bool> requestPermissions() async {
    final status = await Permission.microphone.request();
    return status == PermissionStatus.granted;
  }

  Future<String> _generateFilePath() async {
    final directory = await getApplicationDocumentsDirectory();
    final recordingsDir = Directory(path.join(directory.path, AppConstants.recordingsDirectory));
    
    if (!await recordingsDir.exists()) {
      await recordingsDir.create(recursive: true);
    }
    
    final timestamp = DateFormat('yyyy-MM-dd_HH-mm-ss').format(DateTime.now());
    final fileName = '${AppConstants.filePrefix}_$timestamp.${AppConstants.audioContainer}';
    
    return path.join(recordingsDir.path, fileName);
  }

  Future<RecordingMeta?> startRecording() async {
    try {
      if (!await requestPermissions()) {
        throw Exception('Microphone permission denied');
      }

      final filePath = await _generateFilePath();
      _currentFilePath = filePath;
      _recordingStartTime = DateTime.now();

      // Configure recording with AAC codec at 64kbps
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          bitRate: AppConstants.audioBitrate,
          sampleRate: 44100,
          numChannels: 1,
        ),
        path: filePath,
      );

      recordingState.value = RecordingState.recording;
      
      // Start duration timer
      _durationTimer?.cancel();
      _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (_recordingStartTime != null) {
          recordingDuration.value = DateTime.now().difference(_recordingStartTime!);
        }
      });

      // Auto-stop after 5 minutes
      _autoStopTimer?.cancel();
      _autoStopTimer = Timer(const Duration(seconds: AppConstants.maxRecordingSeconds), () {
        stopRecording();
      });

      _currentRecording = RecordingMeta(
        localPath: filePath,
        fileName: path.basename(filePath),
        createdAt: _recordingStartTime!,
      );

      return _currentRecording;
    } catch (e) {
      debugPrint('Error starting recording: $e');
      recordingState.value = RecordingState.idle;
      return null;
    }
  }

  Future<void> pauseRecording() async {
    if (recordingState.value == RecordingState.recording) {
      await _recorder.pause();
      recordingState.value = RecordingState.paused;
      _durationTimer?.cancel();
    }
  }

  Future<void> resumeRecording() async {
    if (recordingState.value == RecordingState.paused) {
      await _recorder.resume();
      recordingState.value = RecordingState.recording;
      
      // Resume duration timer
      _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (_recordingStartTime != null) {
          recordingDuration.value = DateTime.now().difference(_recordingStartTime!);
        }
      });
    }
  }

  Future<RecordingMeta?> stopRecording() async {
    if (recordingState.value == RecordingState.idle) return null;
    
    try {
      final filePath = await _recorder.stop();
      
      _durationTimer?.cancel();
      _autoStopTimer?.cancel();
      
      recordingState.value = RecordingState.idle;
      
      if (filePath != null && _currentRecording != null) {
        // Update recording metadata with final info
        final file = File(filePath);
        final fileStats = await file.stat();
        
        _currentRecording = _currentRecording!.copyWith(
          durationSec: recordingDuration.value.inSeconds.toDouble(),
          sizeBytes: fileStats.size,
        );
        
        // Reset state
        recordingDuration.value = Duration.zero;
        _recordingStartTime = null;
        _currentFilePath = null;
        
        return _currentRecording;
      }
    } catch (e) {
      debugPrint('Error stopping recording: $e');
    }
    
    recordingDuration.value = Duration.zero;
    return null;
  }

  Future<void> cancelRecording() async {
    if (recordingState.value != RecordingState.idle) {
      final filePath = await _recorder.stop();
      
      // Delete the file
      if (filePath != null) {
        try {
          await File(filePath).delete();
        } catch (e) {
          debugPrint('Error deleting cancelled recording: $e');
        }
      }
      
      _durationTimer?.cancel();
      _autoStopTimer?.cancel();
      recordingState.value = RecordingState.idle;
      recordingDuration.value = Duration.zero;
      _recordingStartTime = null;
      _currentFilePath = null;
      _currentRecording = null;
    }
  }

  void dispose() {
    _durationTimer?.cancel();
    _autoStopTimer?.cancel();
    _recorder.dispose();
    recordingDuration.dispose();
    recordingState.dispose();
  }
}

enum RecordingState {
  idle,
  recording,
  paused,
}