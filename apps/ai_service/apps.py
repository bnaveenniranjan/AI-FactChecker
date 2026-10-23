"""App configuration for the AI service application."""

from django.apps import AppConfig


class AiServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_service'
    label = 'ai_service'
    verbose_name = 'AI Service (Gemini)'
