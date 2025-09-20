enum EditActionType { cut }

class EditAction {
  final EditActionType type;
  final int startMs;
  final int endMs;
  final String? snapshotPath;

  EditAction({
    required this.type,
    required this.startMs,
    required this.endMs,
    this.snapshotPath,
  });

  EditAction copyWith({
    EditActionType? type,
    int? startMs,
    int? endMs,
    String? snapshotPath,
  }) {
    return EditAction(
      type: type ?? this.type,
      startMs: startMs ?? this.startMs,
      endMs: endMs ?? this.endMs,
      snapshotPath: snapshotPath ?? this.snapshotPath,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type.toString().split('.').last,
      'startMs': startMs,
      'endMs': endMs,
      'snapshotPath': snapshotPath,
    };
  }

  factory EditAction.fromJson(Map<String, dynamic> json) {
    return EditAction(
      type: EditActionType.values.firstWhere(
        (e) => e.toString().split('.').last == json['type'],
      ),
      startMs: json['startMs'],
      endMs: json['endMs'],
      snapshotPath: json['snapshotPath'],
    );
  }
}