import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/recording/recording_provider.dart';
import 'package:voicenote/recording/recording_service.dart';
import 'package:voicenote/constants/app_constants.dart';

class RecordingControls extends ConsumerWidget {
  const RecordingControls({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recordingService = ref.watch(recordingServiceProvider);
    
    return ValueListenableBuilder<RecordingState>(
      valueListenable: recordingService.recordingState,
      builder: (context, state, _) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Timer display
            ValueListenableBuilder<Duration>(
              valueListenable: recordingService.recordingDuration,
              builder: (context, duration, _) {
                final minutes = duration.inMinutes;
                final seconds = duration.inSeconds % 60;
                final remaining = AppConstants.maxRecordingSeconds - duration.inSeconds;
                final remainingMin = remaining ~/ 60;
                final remainingSec = remaining % 60;
                
                return Column(
                  children: [
                    Text(
                      '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}',
                      style: Theme.of(context).textTheme.displayMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                    if (state != RecordingState.idle)
                      Text(
                        'Remaining: ${remainingMin.toString().padLeft(2, '0')}:${remainingSec.toString().padLeft(2, '0')}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.grey.shade600,
                        ),
                      ),
                    const SizedBox(height: 8),
                    if (state != RecordingState.idle)
                      LinearProgressIndicator(
                        value: duration.inSeconds / AppConstants.maxRecordingSeconds,
                        minHeight: 4,
                      ),
                  ],
                );
              },
            ),
            
            const SizedBox(height: 40),
            
            // Recording controls
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Start/Stop button
                if (state == RecordingState.idle)
                  _RecordButton(
                    onPressed: () async {
                      final recording = await recordingService.startRecording();
                      if (recording != null) {
                        ref.read(lastRecordingProvider.notifier).state = recording;
                      }
                    },
                    icon: Icons.mic,
                    color: Colors.red,
                    size: 80,
                  )
                else
                  _RecordButton(
                    onPressed: () async {
                      final recording = await recordingService.stopRecording();
                      if (recording != null) {
                        ref.read(lastRecordingProvider.notifier).state = recording;
                      }
                    },
                    icon: Icons.stop,
                    color: Colors.grey.shade700,
                    size: 80,
                  ),
                
                const SizedBox(width: 40),
                
                // Pause/Resume button
                if (state != RecordingState.idle)
                  _RecordButton(
                    onPressed: () async {
                      if (state == RecordingState.recording) {
                        await recordingService.pauseRecording();
                      } else {
                        await recordingService.resumeRecording();
                      }
                    },
                    icon: state == RecordingState.recording
                        ? Icons.pause
                        : Icons.play_arrow,
                    color: Colors.blue,
                    size: 60,
                  ),
              ],
            ),
            
            const SizedBox(height: 20),
            
            // Status text
            Text(
              _getStatusText(state),
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: _getStatusColor(state),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        );
      },
    );
  }

  String _getStatusText(RecordingState state) {
    switch (state) {
      case RecordingState.idle:
        return 'Ready to record';
      case RecordingState.recording:
        return 'Recording...';
      case RecordingState.paused:
        return 'Paused';
    }
  }

  Color _getStatusColor(RecordingState state) {
    switch (state) {
      case RecordingState.idle:
        return Colors.grey;
      case RecordingState.recording:
        return Colors.red;
      case RecordingState.paused:
        return Colors.orange;
    }
  }
}

class _RecordButton extends StatelessWidget {
  final VoidCallback onPressed;
  final IconData icon;
  final Color color;
  final double size;

  const _RecordButton({
    required this.onPressed,
    required this.icon,
    required this.color,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      elevation: 4,
      shape: const CircleBorder(),
      color: color,
      child: InkWell(
        onTap: onPressed,
        customBorder: const CircleBorder(),
        child: SizedBox(
          width: size,
          height: size,
          child: Icon(
            icon,
            color: Colors.white,
            size: size * 0.5,
          ),
        ),
      ),
    );
  }
}