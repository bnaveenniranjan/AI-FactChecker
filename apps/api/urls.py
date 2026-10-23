"""API routes."""

from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    # Research
    path('v1/research/', views.ResearchView.as_view(), name='research-create'),
    path('v1/research/<int:pk>/', views.ResearchDetailView.as_view(), name='research-detail'),

    # Schemes
    path('v1/schemes/', views.SchemeListView.as_view(), name='scheme-list'),
    path('v1/schemes/<int:pk>/', views.SchemeDetailView.as_view(), name='scheme-detail'),
    path('v1/schemes/<int:pk>/timeline/', views.SchemeTimelineView.as_view(), name='scheme-timeline'),
    path('v1/schemes/<int:pk>/budgets/', views.SchemeBudgetView.as_view(), name='scheme-budgets'),
    path('v1/schemes/<int:pk>/leadership/', views.SchemeLeadershipView.as_view(), name='scheme-leadership'),

    # Fact check
    path('v1/fact-check/', views.FactCheckView.as_view(), name='fact-check-create'),

    # Sources
    path('v1/sources/<int:pk>/', views.SourceDetailView.as_view(), name='source-detail'),

    # AI
    path('v1/gemini/status/', views.GeminiStatusView.as_view(), name='gemini-status'),
    path('v1/gemini/configure/', views.GeminiConfigureView.as_view(), name='gemini-configure'),
]
