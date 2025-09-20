from django.contrib import admin
from .models import VoiceRecording, VoiceNote


@admin.register(VoiceRecording)
class VoiceRecordingAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_name', 'status', 'mime_type', 'size_bytes', 'duration_sec', 'created_at']
    list_filter = ['status', 'mime_type', 'created_at']
    search_fields = ['original_name', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(VoiceNote)
class VoiceNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'voice', 'format', 'size_bytes', 'created_at']
    list_filter = ['format', 'created_at']
    search_fields = ['id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']