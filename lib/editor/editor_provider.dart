import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/editor/editor_service.dart';
import 'package:voicenote/models/editor_state.dart';

final editorServiceProvider = Provider<EditorService>((ref) {
  final service = EditorService();
  ref.onDispose(() => service.dispose());
  return service;
});

final editorStateProvider = StateNotifierProvider<EditorStateNotifier, EditorState>((ref) {
  return EditorStateNotifier(ref.watch(editorServiceProvider));
});

class EditorStateNotifier extends StateNotifier<EditorState> {
  final EditorService _service;

  EditorStateNotifier(this._service) : super(EditorState());

  Future<void> loadFile(String filePath) async {
    state = await _service.loadFile(filePath);
  }

  void setSelection(int startMs, int endMs) {
    _service.setSelection(startMs, endMs);
    state = _service.state;
  }

  void clearSelection() {
    _service.clearSelection();
    state = _service.state;
  }

  Future<void> performCut() async {
    state = await _service.performCut();
  }

  Future<void> performUndo() async {
    state = await _service.performUndo();
  }
}