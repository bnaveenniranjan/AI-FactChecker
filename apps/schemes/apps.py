"""App configuration for the schemes application."""

from django.apps import AppConfig


class SchemesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.schemes'
    label = 'schemes'
    verbose_name = 'Government Schemes'
