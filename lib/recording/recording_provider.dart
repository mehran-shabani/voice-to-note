import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/recording/recording_service.dart';
import 'package:voicenote/models/recording_meta.dart';

final recordingServiceProvider = Provider<RecordingService>((ref) {
  final service = RecordingService();
  ref.onDispose(() => service.dispose());
  return service;
});

final recordingStateProvider = Provider<ValueNotifier<RecordingState>>((ref) {
  return ref.watch(recordingServiceProvider).recordingState;
});

final recordingDurationProvider = Provider<ValueNotifier<Duration>>((ref) {
  return ref.watch(recordingServiceProvider).recordingDuration;
});

final lastRecordingProvider = StateProvider<RecordingMeta?>((ref) => null);