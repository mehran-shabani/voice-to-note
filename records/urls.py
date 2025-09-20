"""
URL configuration for records app.
"""
from django.urls import path
from . import views

app_name = 'records'

urlpatterns = [
    path('voices/', views.upload_voice, name='upload_voice'),
]