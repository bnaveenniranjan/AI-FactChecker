"""WSGI config for the AI Government Scheme Fact Checker project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fact_checker.settings')
application = get_wsgi_application()
