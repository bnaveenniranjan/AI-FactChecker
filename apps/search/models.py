"""
Models for the search app — research jobs and caching.

ResearchJob tracks the lifecycle of a research request.
ResearchCache stores results for reuse within the configured TTL.
"""

from django.db import models
from django.utils import timezone


class ResearchJob(models.Model):
    """
    Tracks the lifecycle of a scheme research request.

    Supports both synchronous (immediate) and asynchronous (Celery) execution.
    """

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.BigAutoField(primary_key=True)
    query = models.TextField(help_text='Original user query')
    normalized_query = models.TextField(
        blank=True,
        help_text='Normalized form used for cache lookup',
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='research_jobs',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    result = models.JSONField(
        null=True,
        blank=True,
        help_text='Structured research result (ResearchResultSchema as JSON)',
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error details if the job failed',
    )
    sources_found = models.PositiveIntegerField(default=0)
    sources_fetched = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='search_job_status_idx'),
        ]
        verbose_name = 'Research Job'
        verbose_name_plural = 'Research Jobs'

    def mark_started(self):
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, result: dict):
        self.status = self.STATUS_COMPLETED
        self.result = result
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'result', 'completed_at'])

    def mark_failed(self, error: str):
        self.status = self.STATUS_FAILED
        self.error_message = error
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])

    def __str__(self) -> str:
        return f'Job #{self.pk} [{self.status}] {self.query[:60]}'


class ResearchCache(models.Model):
    """
    Caches research results for a normalized query to avoid redundant API calls.

    Results are considered fresh within RESEARCH_CACHE_TTL_SECONDS (from settings).
    """

    id = models.BigAutoField(primary_key=True)
    cache_key = models.CharField(
        max_length=64,
        unique=True,
        help_text='SHA-256 hash of normalized_query',
    )
    normalized_query = models.TextField()
    scheme = models.ForeignKey(
        'schemes.Scheme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='research_caches',
    )
    result = models.JSONField(help_text='Cached ResearchResultSchema as JSON')
    job = models.ForeignKey(
        ResearchJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cache_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text='Cache expiry timestamp')

    class Meta:
        indexes = [
            models.Index(fields=['cache_key'], name='search_cache_key_idx'),
            models.Index(fields=['expires_at'], name='search_cache_expiry_idx'),
        ]
        verbose_name = 'Research Cache'
        verbose_name_plural = 'Research Cache Entries'

    @property
    def is_fresh(self) -> bool:
        """Return True if cache entry has not expired."""
        return timezone.now() < self.expires_at

    def __str__(self) -> str:
        return f'Cache [{self.cache_key[:8]}…] expires {self.expires_at:%Y-%m-%d %H:%M}'
