"""Fact check app config."""

from django.apps import AppConfig


class FactcheckConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.factcheck'
    label = 'factcheck'
    verbose_name = 'Fact Checking'
