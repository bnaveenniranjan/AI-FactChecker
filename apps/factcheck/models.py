"""Fact check models."""

from django.db import models


class Claim(models.Model):
    """Claim to verify."""

    STATUS_SUPPORTED = 'supported'
    STATUS_CONTRADICTED = 'contradicted'
    STATUS_PARTIAL = 'partially_supported'
    STATUS_INSUFFICIENT = 'insufficient_evidence'
    STATUS_OUTDATED = 'outdated'
    STATUS_PENDING = 'pending'

    VERDICT_CHOICES = [
        (STATUS_SUPPORTED, 'Supported by evidence'),
        (STATUS_CONTRADICTED, 'Contradicted by evidence'),
        (STATUS_PARTIAL, 'Partially supported'),
        (STATUS_INSUFFICIENT, 'Insufficient evidence'),
        (STATUS_OUTDATED, 'Outdated information'),
        (STATUS_PENDING, 'Pending verification'),
    ]

    CONFIDENCE_HIGH = 'high'
    CONFIDENCE_MEDIUM = 'medium'
    CONFIDENCE_LOW = 'low'
    CONFIDENCE_CHOICES = [
        (CONFIDENCE_HIGH, 'High — strong evidence base'),
        (CONFIDENCE_MEDIUM, 'Medium — partial or indirect evidence'),
        (CONFIDENCE_LOW, 'Low — limited or conflicting evidence'),
    ]

    id = models.BigAutoField(primary_key=True)
    claim_text = models.TextField(
        help_text='The original claim as submitted or extracted',
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claims',
    )
    verdict = models.CharField(
        max_length=30,
        choices=VERDICT_CHOICES,
        default=STATUS_PENDING,
    )
    explanation = models.TextField(
        blank=True,
        help_text='Short human-readable explanation of the verdict',
    )
    confidence = models.CharField(
        max_length=20,
        choices=CONFIDENCE_CHOICES,
        blank=True,
        help_text='Evidence strength assessment',
    )
    confidence_explanation = models.TextField(
        blank=True,
        help_text='Explanation of why this confidence level was assigned',
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this claim was last verified',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Claim'
        verbose_name_plural = 'Claims'

    def __str__(self) -> str:
        preview = self.claim_text[:100] + '…' if len(self.claim_text) > 100 else self.claim_text
        return f'[{self.verdict}] {preview}'


class ClaimEvidence(models.Model):
    """Evidence for a claim."""

    SUPPORT_SUPPORTS = 'supports'
    SUPPORT_CONTRADICTS = 'contradicts'
    SUPPORT_NEUTRAL = 'neutral'
    SUPPORT_CHOICES = [
        (SUPPORT_SUPPORTS, 'Supports the claim'),
        (SUPPORT_CONTRADICTS, 'Contradicts the claim'),
        (SUPPORT_NEUTRAL, 'Neutral / contextual'),
    ]

    id = models.BigAutoField(primary_key=True)
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='evidence_links',
    )
    excerpt = models.ForeignKey(
        'sources.EvidenceExcerpt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claim_links',
    )
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claim_evidence',
    )
    stance = models.CharField(
        max_length=20,
        choices=SUPPORT_CHOICES,
        default=SUPPORT_NEUTRAL,
    )
    relevance_note = models.TextField(
        blank=True,
        help_text='Why this evidence is relevant to the claim',
    )
    publication_date = models.DateField(
        null=True,
        blank=True,
        help_text='Publication date of the source used for this evidence',
    )
    event_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date of the event described in the evidence',
    )

    class Meta:
        verbose_name = 'Claim Evidence'
        verbose_name_plural = 'Claim Evidence'

    def __str__(self) -> str:
        return f'{self.claim} ← [{self.stance}] {self.source}'


class FactCheckResult(models.Model):
    """Fact check result record."""

    id = models.BigAutoField(primary_key=True)
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='fact_check_results',
    )
    ai_model_used = models.CharField(
        max_length=100,
        blank=True,
        help_text='Gemini model identifier used for this fact check',
    )
    raw_ai_response = models.JSONField(
        null=True,
        blank=True,
        help_text='Structured JSON output from Gemini (for audit)',
    )
    processing_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Total processing time in milliseconds',
    )
    sources_searched = models.PositiveIntegerField(default=0)
    sources_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fact Check Result'
        verbose_name_plural = 'Fact Check Results'

    def __str__(self) -> str:
        return f'FactCheck #{self.pk} — {self.claim}'
