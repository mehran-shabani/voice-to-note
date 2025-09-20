import 'package:uuid/uuid.dart';

class RecordingMeta {
  final String id;
  final String localPath;
  final String fileName;
  final DateTime createdAt;
  final double? durationSec;
  final int? sizeBytes;
  final String format;

  RecordingMeta({
    String? id,
    required this.localPath,
    required this.fileName,
    DateTime? createdAt,
    this.durationSec,
    this.sizeBytes,
    this.format = 'm4a',
  })  : id = id ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now();

  RecordingMeta copyWith({
    String? id,
    String? localPath,
    String? fileName,
    DateTime? createdAt,
    double? durationSec,
    int? sizeBytes,
    String? format,
  }) {
    return RecordingMeta(
      id: id ?? this.id,
      localPath: localPath ?? this.localPath,
      fileName: fileName ?? this.fileName,
      createdAt: createdAt ?? this.createdAt,
      durationSec: durationSec ?? this.durationSec,
      sizeBytes: sizeBytes ?? this.sizeBytes,
      format: format ?? this.format,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'localPath': localPath,
      'fileName': fileName,
      'createdAt': createdAt.toIso8601String(),
      'durationSec': durationSec,
      'sizeBytes': sizeBytes,
      'format': format,
    };
  }

  factory RecordingMeta.fromJson(Map<String, dynamic> json) {
    return RecordingMeta(
      id: json['id'],
      localPath: json['localPath'],
      fileName: json['fileName'],
      createdAt: DateTime.parse(json['createdAt']),
      durationSec: json['durationSec']?.toDouble(),
      sizeBytes: json['sizeBytes'],
      format: json['format'] ?? 'm4a',
    );
  }
}