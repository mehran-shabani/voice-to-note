import uuid
from django.db import models


class VoiceRecording(models.Model):
    """Model to store uploaded voice recordings and their metadata."""
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='voices/%Y/%m/%d/')
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    duration_sec = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.original_name} ({self.status})"


class VoiceNote(models.Model):
    """Model to store transcribed notes from voice recordings."""
    
    FORMAT_CHOICES = [
        ('txt', 'Plain Text'),
        ('md', 'Markdown'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voice = models.ForeignKey(
        VoiceRecording, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='notes'
    )
    file = models.FileField(upload_to='notes/%Y/%m/%d/')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='txt')
    size_bytes = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Note for {self.voice.original_name if self.voice else 'Unknown'}"