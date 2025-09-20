import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/upload/upload_service.dart';

final uploadServiceProvider = Provider<UploadService>((ref) {
  final service = UploadService();
  ref.onDispose(() => service.dispose());
  return service;
});

final uploadProgressProvider = StateProvider<double>((ref) => 0.0);

final uploadStatusProvider = StateProvider<UploadStatus>((ref) => UploadStatus.idle);

enum UploadStatus {
  idle,
  uploading,
  success,
  error,
}