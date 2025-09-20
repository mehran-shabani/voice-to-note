import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/widgets/recording_controls.dart';
import 'package:voicenote/widgets/editor_panel.dart';
import 'package:voicenote/widgets/upload_button.dart';
import 'package:voicenote/constants/app_constants.dart';
import 'package:voicenote/recording/recording_provider.dart';
import 'package:voicenote/editor/editor_provider.dart';

class MainScreen extends ConsumerStatefulWidget {
  const MainScreen({super.key});

  @override
  ConsumerState<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends ConsumerState<MainScreen> {
  bool _showEditor = false;

  @override
  Widget build(BuildContext context) {
    final lastRecording = ref.watch(lastRecordingProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text(AppConstants.appName),
        centerTitle: true,
        elevation: 2,
      ),
      body: Row(
        children: [
          // Left panel - Editor
          if (_showEditor)
            Container(
              width: 350,
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                border: Border(
                  right: BorderSide(
                    color: Colors.grey.shade300,
                    width: 1,
                  ),
                ),
              ),
              child: EditorPanel(
                onClose: () {
                  setState(() {
                    _showEditor = false;
                  });
                },
              ),
            ),
          
          // Center - Recording controls
          Expanded(
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const RecordingControls(),
                  const SizedBox(height: 40),
                  
                  // Show editor button if we have a recording
                  if (lastRecording != null && !_showEditor)
                    ElevatedButton.icon(
                      onPressed: () async {
                        // Load the last recording into editor
                        await ref.read(editorStateProvider.notifier)
                            .loadFile(lastRecording.localPath);
                        setState(() {
                          _showEditor = true;
                        });
                      },
                      icon: const Icon(Icons.edit),
                      label: const Text('Edit Last Recording'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 12,
                        ),
                      ),
                    ),
                  
                  const SizedBox(height: 20),
                  
                  // Upload button
                  if (lastRecording != null)
                    UploadButton(
                      filePath: lastRecording.localPath,
                      fileName: lastRecording.fileName,
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}