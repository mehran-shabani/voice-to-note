import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:voicenote/upload/upload_provider.dart';

class UploadButton extends ConsumerWidget {
  final String filePath;
  final String fileName;

  const UploadButton({
    super.key,
    required this.filePath,
    required this.fileName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final uploadStatus = ref.watch(uploadStatusProvider);
    final uploadProgress = ref.watch(uploadProgressProvider);
    final uploadService = ref.watch(uploadServiceProvider);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (uploadStatus == UploadStatus.uploading) ...[
          SizedBox(
            width: 200,
            child: Column(
              children: [
                LinearProgressIndicator(
                  value: uploadProgress,
                  minHeight: 8,
                ),
                const SizedBox(height: 8),
                Text(
                  '${(uploadProgress * 100).toStringAsFixed(0)}%',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () {
              uploadService.cancelUpload();
              ref.read(uploadStatusProvider.notifier).state = UploadStatus.idle;
              ref.read(uploadProgressProvider.notifier).state = 0.0;
            },
            child: const Text('Cancel'),
          ),
        ] else ...[
          ElevatedButton.icon(
            onPressed: uploadStatus == UploadStatus.uploading
                ? null
                : () async {
                    ref.read(uploadStatusProvider.notifier).state = 
                        UploadStatus.uploading;
                    ref.read(uploadProgressProvider.notifier).state = 0.0;

                    final result = await uploadService.uploadFile(
                      filePath,
                      onProgress: (progress) {
                        ref.read(uploadProgressProvider.notifier).state = progress;
                      },
                    );

                    if (result.success) {
                      ref.read(uploadStatusProvider.notifier).state = 
                          UploadStatus.success;
                      
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Upload successful! (${result.statusCode})',
                            ),
                            backgroundColor: Colors.green,
                          ),
                        );
                      }
                      
                      // Reset after delay
                      await Future.delayed(const Duration(seconds: 2));
                      ref.read(uploadStatusProvider.notifier).state = 
                          UploadStatus.idle;
                    } else {
                      ref.read(uploadStatusProvider.notifier).state = 
                          UploadStatus.error;
                      
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(result.message),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                      
                      // Reset after delay
                      await Future.delayed(const Duration(seconds: 3));
                      ref.read(uploadStatusProvider.notifier).state = 
                          UploadStatus.idle;
                    }
                    
                    ref.read(uploadProgressProvider.notifier).state = 0.0;
                  },
            icon: _getUploadIcon(uploadStatus),
            label: Text(_getUploadText(uploadStatus)),
            style: ElevatedButton.styleFrom(
              backgroundColor: _getUploadColor(uploadStatus),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 12,
              ),
            ),
          ),
          
          const SizedBox(height: 8),
          
          Text(
            fileName,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey.shade600,
            ),
          ),
        ],
      ],
    );
  }

  Icon _getUploadIcon(UploadStatus status) {
    switch (status) {
      case UploadStatus.idle:
        return const Icon(Icons.cloud_upload);
      case UploadStatus.uploading:
        return const Icon(Icons.hourglass_empty);
      case UploadStatus.success:
        return const Icon(Icons.check_circle);
      case UploadStatus.error:
        return const Icon(Icons.error);
    }
  }

  String _getUploadText(UploadStatus status) {
    switch (status) {
      case UploadStatus.idle:
        return 'Upload';
      case UploadStatus.uploading:
        return 'Uploading...';
      case UploadStatus.success:
        return 'Uploaded!';
      case UploadStatus.error:
        return 'Upload Failed';
    }
  }

  Color _getUploadColor(UploadStatus status) {
    switch (status) {
      case UploadStatus.idle:
        return Colors.blue;
      case UploadStatus.uploading:
        return Colors.orange;
      case UploadStatus.success:
        return Colors.green;
      case UploadStatus.error:
        return Colors.red;
    }
  }
}