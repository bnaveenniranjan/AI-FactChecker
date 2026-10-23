"""
Models for the sources app.

Manages external source records, evidence excerpts, and provenance metadata.
All retrieved documents are treated as untrusted data — never as instructions.
"""

import hashlib

from django.db import models


class Source(models.Model):
    """
    A retrieved external document used as evidence for scheme facts.

    Prefer primary sources (official government portals, gazette notifications,
    budget documents, PIB releases) for official dates and allocations.
    Use reputable secondary sources for context and analysis.

    A content_hash is computed from the URL to aid deduplication.
    """

    CATEGORY_OFFICIAL_PORTAL = 'official_portal'
    CATEGORY_GAZETTE = 'gazette'
    CATEGORY_BUDGET_DOC = 'budget_document'
    CATEGORY_PIB = 'pib'
    CATEGORY_PARLIAMENT = 'parliament'
    CATEGORY_CAG = 'cag_report'
    CATEGORY_NEWS = 'news'
    CATEGORY_RESEARCH = 'research'
    CATEGORY_OTHER = 'other'

    SOURCE_CATEGORY_CHOICES = [
        (CATEGORY_OFFICIAL_PORTAL, 'Official Government Portal'),
        (CATEGORY_GAZETTE, 'Official Gazette / Notification'),
        (CATEGORY_BUDGET_DOC, 'Budget Document'),
        (CATEGORY_PIB, 'Press Information Bureau (PIB)'),
        (CATEGORY_PARLIAMENT, 'Parliament Record'),
        (CATEGORY_CAG, 'CAG Report'),
        (CATEGORY_NEWS, 'News Organisation'),
        (CATEGORY_RESEARCH, 'Research / Think Tank'),
        (CATEGORY_OTHER, 'Other'),
    ]

    RELIABILITY_HIGH = 'high'
    RELIABILITY_MEDIUM = 'medium'
    RELIABILITY_LOW = 'low'
    RELIABILITY_UNKNOWN = 'unknown'
    RELIABILITY_CHOICES = [
        (RELIABILITY_HIGH, 'High — Primary official source'),
        (RELIABILITY_MEDIUM, 'Medium — Reputable secondary source'),
        (RELIABILITY_LOW, 'Low — Unreliable or unverified'),
        (RELIABILITY_UNKNOWN, 'Unknown'),
    ]

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=500, blank=True)
    url = models.URLField(max_length=2000, unique=True)
    publisher = models.CharField(max_length=300, blank=True)
    source_category = models.CharField(
        max_length=30,
        choices=SOURCE_CATEGORY_CHOICES,
        default=CATEGORY_OTHER,
    )
    published_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date the source was originally published',
    )
    retrieved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When we last fetched this URL',
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text='SHA-256 of the URL for deduplication',
    )
    reliability = models.CharField(
        max_length=20,
        choices=RELIABILITY_CHOICES,
        default=RELIABILITY_UNKNOWN,
    )
    schemes = models.ManyToManyField(
        'schemes.Scheme',
        blank=True,
        related_name='sources',
        help_text='Schemes this source is relevant to',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_date', '-retrieved_at']
        indexes = [
            models.Index(fields=['content_hash'], name='source_hash_idx'),
            models.Index(fields=['source_category'], name='source_category_idx'),
            models.Index(fields=['reliability'], name='source_reliability_idx'),
        ]
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'

    def save(self, *args, **kwargs):
        if self.url and not self.content_hash:
            self.content_hash = hashlib.sha256(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title or self.url


class EvidenceExcerpt(models.Model):
    """
    A relevant excerpt from a source document.

    Each excerpt is linked to a source, and optionally to a specific
    scheme, timeline event, or factual claim. Do NOT store fabricated
    or paraphrased excerpts — only text retrieved from the actual source.
    """

    id = models.BigAutoField(primary_key=True)
    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name='excerpts',
    )
    text = models.TextField(
        help_text='The exact relevant passage retrieved from the source',
    )
    page_or_section = models.CharField(
        max_length=100,
        blank=True,
        help_text='Page number, section, or paragraph reference within the source',
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evidence_excerpts',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evidence Excerpt'
        verbose_name_plural = 'Evidence Excerpts'

    def __str__(self) -> str:
        preview = self.text[:80] + '…' if len(self.text) > 80 else self.text
        return f'[{self.source}] {preview}'
