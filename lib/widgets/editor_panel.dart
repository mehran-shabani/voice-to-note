import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/editor/editor_provider.dart';
import 'package:voicenote/editor/editor_service.dart';
import 'package:voicenote/recording/recording_provider.dart';

class EditorPanel extends ConsumerStatefulWidget {
  final VoidCallback onClose;

  const EditorPanel({
    super.key,
    required this.onClose,
  });

  @override
  ConsumerState<EditorPanel> createState() => _EditorPanelState();
}

class _EditorPanelState extends ConsumerState<EditorPanel> {
  final _startController = TextEditingController();
  final _endController = TextEditingController();
  
  @override
  void dispose() {
    _startController.dispose();
    _endController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final editorState = ref.watch(editorStateProvider);
    final editorService = ref.watch(editorServiceProvider);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(16),
          color: Theme.of(context).primaryColor.withOpacity(0.1),
          child: Row(
            children: [
              Icon(Icons.edit, color: Theme.of(context).primaryColor),
              const SizedBox(width: 8),
              Text(
                'Audio Editor',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              IconButton(
                onPressed: widget.onClose,
                icon: const Icon(Icons.close),
              ),
            ],
          ),
        ),
        
        // Editor controls
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // File info
                if (editorState.sourceFile != null) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Loaded File',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            editorState.sourceFile!.split('/').last,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          if (editorState.totalDurationMs != null) ...[
                            const SizedBox(height: 4),
                            Text(
                              'Duration: ${_formatDuration(editorState.totalDurationMs!)}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 20),
                  
                  // Selection controls
                  Text(
                    'Select Range to Cut',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _startController,
                          decoration: const InputDecoration(
                            labelText: 'Start (seconds)',
                            border: OutlineInputBorder(),
                            contentPadding: EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                          ),
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _endController,
                          decoration: const InputDecoration(
                            labelText: 'End (seconds)',
                            border: OutlineInputBorder(),
                            contentPadding: EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                          ),
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 12),
                  
                  ElevatedButton(
                    onPressed: () {
                      final startSec = double.tryParse(_startController.text);
                      final endSec = double.tryParse(_endController.text);
                      
                      if (startSec != null && endSec != null && endSec > startSec) {
                        final startMs = (startSec * 1000).toInt();
                        final endMs = (endSec * 1000).toInt();
                        
                        ref.read(editorStateProvider.notifier)
                            .setSelection(startMs, endMs);
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Invalid range. End must be greater than start.'),
                          ),
                        );
                      }
                    },
                    child: const Text('Set Selection'),
                  ),
                  
                  if (editorState.hasSelection) ...[
                    const SizedBox(height: 8),
                    Card(
                      color: Colors.blue.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(8),
                        child: Row(
                          children: [
                            Icon(Icons.info_outline, 
                                size: 16, 
                                color: Colors.blue.shade700),
                            const SizedBox(width: 8),
                            Text(
                              'Selected: ${_formatMs(editorState.selectionStartMs!)} - ${_formatMs(editorState.selectionEndMs!)}',
                              style: TextStyle(color: Colors.blue.shade700),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  
                  const SizedBox(height: 20),
                  
                  // Action buttons
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: editorState.canCut
                              ? () async {
                                  try {
                                    await ref.read(editorStateProvider.notifier)
                                        .performCut();
                                    _startController.clear();
                                    _endController.clear();
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                          content: Text('Cut successful'),
                                        ),
                                      );
                                    }
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text('Cut failed: $e'),
                                          backgroundColor: Colors.red,
                                        ),
                                      );
                                    }
                                  }
                                }
                              : null,
                          icon: const Icon(Icons.content_cut),
                          label: const Text('Cut'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.orange,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: editorState.canUndo
                              ? () async {
                                  try {
                                    await ref.read(editorStateProvider.notifier)
                                        .performUndo();
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                          content: Text('Undo successful'),
                                        ),
                                      );
                                    }
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text('Undo failed: $e'),
                                          backgroundColor: Colors.red,
                                        ),
                                      );
                                    }
                                  }
                                }
                              : null,
                          icon: const Icon(Icons.undo),
                          label: const Text('Undo'),
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 12),
                  
                  // Save button
                  ElevatedButton.icon(
                    onPressed: editorState.pendingEdits.isNotEmpty
                        ? () async {
                            try {
                              final savedFile = await editorService.saveEditedFile();
                              ref.read(lastRecordingProvider.notifier).state = savedFile;
                              
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text('Saved as ${savedFile.fileName}'),
                                    backgroundColor: Colors.green,
                                  ),
                                );
                                widget.onClose();
                              }
                            } catch (e) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text('Save failed: $e'),
                                    backgroundColor: Colors.red,
                                  ),
                                );
                              }
                            }
                          }
                        : null,
                    icon: const Icon(Icons.save),
                    label: const Text('Save Edited'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                      minimumSize: const Size.fromHeight(48),
                    ),
                  ),
                  
                  // Edit history
                  if (editorState.pendingEdits.isNotEmpty) ...[
                    const SizedBox(height: 20),
                    Text(
                      'Edit History (${editorState.pendingEdits.length})',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 8),
                    ...editorState.pendingEdits.map((edit) => Card(
                      child: ListTile(
                        dense: true,
                        leading: const Icon(Icons.content_cut, size: 20),
                        title: Text(
                          'Cut: ${_formatMs(edit.startMs)} - ${_formatMs(edit.endMs)}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    )),
                  ],
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  String _formatDuration(double milliseconds) {
    final totalSeconds = (milliseconds / 1000).round();
    final minutes = totalSeconds ~/ 60;
    final seconds = totalSeconds % 60;
    return '${minutes}m ${seconds}s';
  }

  String _formatMs(int milliseconds) {
    final totalSeconds = milliseconds / 1000;
    return '${totalSeconds.toStringAsFixed(1)}s';
  }
}