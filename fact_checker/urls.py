"""Root URL configuration for the AI Government Scheme Fact Checker project."""

from django.contrib import admin
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls', namespace='api')),
]

admin.site.site_header = 'AI Government Scheme Fact Checker'
admin.site.site_title = 'Fact Checker Admin'
admin.site.index_title = 'Administration'
