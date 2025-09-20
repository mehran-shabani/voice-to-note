import 'package:voicenote/models/edit_action.dart';

class EditorState {
  final String? sourceFile;
  final List<EditAction> pendingEdits;
  final bool hasUndo;
  final int? selectionStartMs;
  final int? selectionEndMs;
  final double? totalDurationMs;

  EditorState({
    this.sourceFile,
    this.pendingEdits = const [],
    this.hasUndo = false,
    this.selectionStartMs,
    this.selectionEndMs,
    this.totalDurationMs,
  });

  EditorState copyWith({
    String? sourceFile,
    List<EditAction>? pendingEdits,
    bool? hasUndo,
    int? selectionStartMs,
    int? selectionEndMs,
    double? totalDurationMs,
    bool clearSelection = false,
  }) {
    return EditorState(
      sourceFile: sourceFile ?? this.sourceFile,
      pendingEdits: pendingEdits ?? this.pendingEdits,
      hasUndo: hasUndo ?? this.hasUndo,
      selectionStartMs: clearSelection ? null : (selectionStartMs ?? this.selectionStartMs),
      selectionEndMs: clearSelection ? null : (selectionEndMs ?? this.selectionEndMs),
      totalDurationMs: totalDurationMs ?? this.totalDurationMs,
    );
  }

  bool get hasSelection => selectionStartMs != null && selectionEndMs != null;
  
  bool get canCut => hasSelection && sourceFile != null;
  
  bool get canUndo => hasUndo && pendingEdits.isNotEmpty;
}