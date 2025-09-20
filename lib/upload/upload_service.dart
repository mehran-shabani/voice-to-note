import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:voicenote/constants/app_constants.dart';

class UploadService {
  late final Dio _dio;
  CancelToken? _cancelToken;
  
  UploadService() {
    _dio = Dio(BaseOptions(
      connectTimeout: AppConstants.uploadTimeout,
      receiveTimeout: AppConstants.uploadTimeout,
      sendTimeout: AppConstants.uploadTimeout,
    ));
  }

  Future<UploadResult> uploadFile(
    String filePath, {
    void Function(double progress)? onProgress,
  }) async {
    try {
      final file = File(filePath);
      
      if (!await file.exists()) {
        throw Exception('File does not exist');
      }
      
      final fileName = file.path.split('/').last;
      
      // Create form data with multipart file
      final formData = FormData.fromMap({
        'audio': await MultipartFile.fromFile(
          file.path,
          filename: fileName,
        ),
      });
      
      _cancelToken = CancelToken();
      
      // Send request
      final response = await _dio.post(
        AppConstants.uploadEndpoint,
        data: formData,
        cancelToken: _cancelToken,
        onSendProgress: (sent, total) {
          if (total > 0 && onProgress != null) {
            final progress = sent / total;
            onProgress(progress);
          }
        },
        options: Options(
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        ),
      );
      
      // Handle response - accept both 200 and 201 as success
      if (response.statusCode == 200 || response.statusCode == 201) {
        debugPrint('Upload successful: ${response.statusCode}');
        
        // Extract location header if present
        final locationHeader = response.headers.value('location');
        
        return UploadResult(
          success: true,
          statusCode: response.statusCode!,
          locationUrl: locationHeader,
          message: 'Upload successful',
        );
      } else {
        throw DioException(
          requestOptions: response.requestOptions,
          response: response,
          message: 'Unexpected status code: ${response.statusCode}',
        );
      }
    } on DioException catch (e) {
      debugPrint('Upload error: ${e.message}');
      
      if (e.type == DioExceptionType.cancel) {
        return UploadResult(
          success: false,
          statusCode: 0,
          message: 'Upload cancelled',
        );
      }
      
      String errorMessage = 'Upload failed';
      int statusCode = e.response?.statusCode ?? 0;
      
      if (e.response != null) {
        switch (e.response!.statusCode) {
          case 400:
            errorMessage = 'Invalid file format';
            break;
          case 413:
            errorMessage = 'File too large';
            break;
          case 500:
            errorMessage = 'Server error';
            break;
          default:
            errorMessage = 'Upload failed: ${e.response!.statusCode}';
        }
      } else if (e.type == DioExceptionType.connectionTimeout ||
                 e.type == DioExceptionType.sendTimeout ||
                 e.type == DioExceptionType.receiveTimeout) {
        errorMessage = 'Connection timeout';
      } else if (e.type == DioExceptionType.connectionError) {
        errorMessage = 'Connection error';
      }
      
      return UploadResult(
        success: false,
        statusCode: statusCode,
        message: errorMessage,
      );
    } catch (e) {
      debugPrint('Unexpected upload error: $e');
      return UploadResult(
        success: false,
        statusCode: 0,
        message: 'Unexpected error: $e',
      );
    }
  }

  void cancelUpload() {
    _cancelToken?.cancel('Upload cancelled by user');
  }

  void dispose() {
    cancelUpload();
    _dio.close();
  }
}

class UploadResult {
  final bool success;
  final int statusCode;
  final String? locationUrl;
  final String message;

  UploadResult({
    required this.success,
    required this.statusCode,
    this.locationUrl,
    required this.message,
  });
}