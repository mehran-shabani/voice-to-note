import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;
import 'package:intl/intl.dart';
import 'package:ffmpeg_kit_flutter_audio/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_audio/return_code.dart';
import 'package:just_audio/just_audio.dart';
import 'package:voicenote/constants/app_constants.dart';
import 'package:voicenote/models/edit_action.dart';
import 'package:voicenote/models/editor_state.dart';
import 'package:voicenote/models/recording_meta.dart';

class EditorService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  EditorState _state = EditorState();
  
  EditorState get state => _state;
  
  Future<EditorState> loadFile(String filePath) async {
    try {
      // Get audio duration
      final duration = await _audioPlayer.setFilePath(filePath);
      
      _state = EditorState(
        sourceFile: filePath,
        totalDurationMs: duration?.inMilliseconds.toDouble(),
        pendingEdits: [],
        hasUndo: false,
      );
      
      return _state;
    } catch (e) {
      debugPrint('Error loading file for editing: $e');
      throw Exception('Failed to load audio file');
    }
  }

  void setSelection(int startMs, int endMs) {
    if (_state.sourceFile == null) return;
    
    _state = _state.copyWith(
      selectionStartMs: startMs,
      selectionEndMs: endMs,
    );
  }

  void clearSelection() {
    _state = _state.copyWith(clearSelection: true);
  }

  Future<String> _createSnapshot(String sourceFile) async {
    final directory = await getApplicationDocumentsDirectory();
    final snapshotsDir = Directory(path.join(directory.path, AppConstants.snapshotsDirectory));
    
    if (!await snapshotsDir.exists()) {
      await snapshotsDir.create(recursive: true);
    }
    
    final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
    final snapshotPath = path.join(snapshotsDir.path, 'snapshot_$timestamp.m4a');
    
    await File(sourceFile).copy(snapshotPath);
    return snapshotPath;
  }

  Future<EditorState> performCut() async {
    if (!_state.canCut) {
      throw Exception('Cannot perform cut: no selection or source file');
    }
    
    final sourceFile = _state.sourceFile!;
    final startMs = _state.selectionStartMs!;
    final endMs = _state.selectionEndMs!;
    
    try {
      // Create snapshot for undo
      final snapshotPath = await _createSnapshot(sourceFile);
      
      // Create temp file for output
      final directory = await getApplicationDocumentsDirectory();
      final tempDir = Directory(path.join(directory.path, AppConstants.tempDirectory));
      
      if (!await tempDir.exists()) {
        await tempDir.create(recursive: true);
      }
      
      final tempPath = path.join(tempDir.path, 'temp_cut_${DateTime.now().millisecondsSinceEpoch}.m4a');
      
      // Convert milliseconds to seconds for ffmpeg
      final startSec = startMs / 1000.0;
      final endSec = endMs / 1000.0;
      final durationSec = (_state.totalDurationMs ?? 0) / 1000.0;
      
      // Build ffmpeg command to cut the selected range
      // We'll create two segments (before and after the cut) and concatenate them
      String ffmpegCommand;
      
      if (startSec > 0 && endSec < durationSec) {
        // Cut from middle - need to concatenate before and after parts
        final concatFile = path.join(tempDir.path, 'concat_${DateTime.now().millisecondsSinceEpoch}.txt');
        
        // Create temporary files for segments
        final beforePath = path.join(tempDir.path, 'before_${DateTime.now().millisecondsSinceEpoch}.m4a');
        final afterPath = path.join(tempDir.path, 'after_${DateTime.now().millisecondsSinceEpoch}.m4a');
        
        // Extract before segment
        await FFmpegKit.execute(
          '-i "$sourceFile" -t $startSec -c:a aac -b:a ${AppConstants.audioBitrateKbps}k "$beforePath"'
        );
        
        // Extract after segment
        await FFmpegKit.execute(
          '-i "$sourceFile" -ss $endSec -c:a aac -b:a ${AppConstants.audioBitrateKbps}k "$afterPath"'
        );
        
        // Create concat file
        await File(concatFile).writeAsString(
          "file '$beforePath'\nfile '$afterPath'"
        );
        
        // Concatenate
        ffmpegCommand = '-f concat -safe 0 -i "$concatFile" -c:a aac -b:a ${AppConstants.audioBitrateKbps}k "$tempPath"';
      } else if (startSec == 0) {
        // Cut from beginning
        ffmpegCommand = '-i "$sourceFile" -ss $endSec -c:a aac -b:a ${AppConstants.audioBitrateKbps}k "$tempPath"';
      } else {
        // Cut from end
        ffmpegCommand = '-i "$sourceFile" -t $startSec -c:a aac -b:a ${AppConstants.audioBitrateKbps}k "$tempPath"';
      }
      
      // Execute ffmpeg command
      final session = await FFmpegKit.execute(ffmpegCommand);
      final returnCode = await session.getReturnCode();
      
      if (!ReturnCode.isSuccess(returnCode)) {
        throw Exception('FFmpeg cut operation failed');
      }
      
      // Replace source file with cut version
      await File(tempPath).copy(sourceFile);
      await File(tempPath).delete();
      
      // Create edit action
      final editAction = EditAction(
        type: EditActionType.cut,
        startMs: startMs,
        endMs: endMs,
        snapshotPath: snapshotPath,
      );
      
      // Update state
      final newDuration = await _audioPlayer.setFilePath(sourceFile);
      _state = _state.copyWith(
        pendingEdits: [..._state.pendingEdits, editAction],
        hasUndo: true,
        totalDurationMs: newDuration?.inMilliseconds.toDouble(),
        clearSelection: true,
      );
      
      return _state;
    } catch (e) {
      debugPrint('Error performing cut: $e');
      throw Exception('Failed to cut audio');
    }
  }

  Future<EditorState> performUndo() async {
    if (!_state.canUndo) {
      throw Exception('Cannot undo: no pending edits');
    }
    
    final lastEdit = _state.pendingEdits.last;
    if (lastEdit.snapshotPath == null) {
      throw Exception('No snapshot available for undo');
    }
    
    try {
      // Restore from snapshot
      await File(lastEdit.snapshotPath!).copy(_state.sourceFile!);
      
      // Remove the last edit
      final newEdits = List<EditAction>.from(_state.pendingEdits)..removeLast();
      
      // Update duration
      final newDuration = await _audioPlayer.setFilePath(_state.sourceFile!);
      
      _state = _state.copyWith(
        pendingEdits: newEdits,
        hasUndo: newEdits.isNotEmpty,
        totalDurationMs: newDuration?.inMilliseconds.toDouble(),
      );
      
      // Clean up snapshot
      try {
        await File(lastEdit.snapshotPath!).delete();
      } catch (e) {
        debugPrint('Error deleting snapshot: $e');
      }
      
      return _state;
    } catch (e) {
      debugPrint('Error performing undo: $e');
      throw Exception('Failed to undo');
    }
  }

  Future<RecordingMeta> saveEditedFile() async {
    if (_state.sourceFile == null) {
      throw Exception('No file loaded for editing');
    }
    
    try {
      final directory = await getApplicationDocumentsDirectory();
      final recordingsDir = Directory(path.join(directory.path, AppConstants.recordingsDirectory));
      
      if (!await recordingsDir.exists()) {
        await recordingsDir.create(recursive: true);
      }
      
      // Generate new filename with edited suffix
      final timestamp = DateFormat('yyyy-MM-dd_HH-mm-ss').format(DateTime.now());
      final fileName = '${AppConstants.filePrefix}_${timestamp}${AppConstants.editedSuffix}.${AppConstants.audioContainer}';
      final newPath = path.join(recordingsDir.path, fileName);
      
      // Copy current edited file to new location
      await File(_state.sourceFile!).copy(newPath);
      
      // Get file info
      final file = File(newPath);
      final fileStats = await file.stat();
      final duration = await _audioPlayer.setFilePath(newPath);
      
      // Clean up snapshots
      await _cleanupSnapshots();
      
      return RecordingMeta(
        localPath: newPath,
        fileName: fileName,
        durationSec: duration?.inSeconds.toDouble(),
        sizeBytes: fileStats.size,
      );
    } catch (e) {
      debugPrint('Error saving edited file: $e');
      throw Exception('Failed to save edited file');
    }
  }

  Future<void> _cleanupSnapshots() async {
    for (final edit in _state.pendingEdits) {
      if (edit.snapshotPath != null) {
        try {
          await File(edit.snapshotPath!).delete();
        } catch (e) {
          debugPrint('Error deleting snapshot: $e');
        }
      }
    }
  }

  void dispose() {
    _audioPlayer.dispose();
    _cleanupSnapshots();
  }
}