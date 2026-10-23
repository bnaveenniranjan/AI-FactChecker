"""Scheme models."""

from django.db import models
from django.utils.text import slugify


class Scheme(models.Model):
    """Government welfare scheme."""

    JURISDICTION_CENTRAL = 'central'
    JURISDICTION_STATE = 'state'
    JURISDICTION_JOINT = 'joint'
    JURISDICTION_CHOICES = [
        (JURISDICTION_CENTRAL, 'Central Government'),
        (JURISDICTION_STATE, 'State Government'),
        (JURISDICTION_JOINT, 'Jointly Funded'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_DISCONTINUED = 'discontinued'
    STATUS_MERGED = 'merged'
    STATUS_SUSPENDED = 'suspended'
    STATUS_UNKNOWN = 'unknown'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DISCONTINUED, 'Discontinued'),
        (STATUS_MERGED, 'Merged into another scheme'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_UNKNOWN, 'Status Unknown'),
    ]

    CATEGORY_CHOICES = [
        ('agriculture', 'Agriculture & Farmers Welfare'),
        ('education', 'Education'),
        ('health', 'Health & Medical'),
        ('housing', 'Housing'),
        ('infrastructure', 'Infrastructure'),
        ('livelihood', 'Livelihood & Employment'),
        ('nutrition', 'Nutrition & Food Security'),
        ('social_protection', 'Social Protection'),
        ('women_child', 'Women & Child Development'),
        ('other', 'Other'),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=300,
        unique=True,
        help_text='Official full name of the scheme',
    )
    slug = models.SlugField(
        max_length=320,
        unique=True,
        blank=True,
        help_text='URL-safe identifier auto-generated from name',
    )
    abbreviation = models.CharField(
        max_length=50,
        blank=True,
        help_text='Common abbreviation (e.g. PM-KISAN, MGNREGA)',
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
    )
    jurisdiction = models.CharField(
        max_length=20,
        choices=JURISDICTION_CHOICES,
        default=JURISDICTION_CENTRAL,
    )
    country = models.CharField(
        max_length=100,
        default='India',
        help_text='Country of jurisdiction (supports future expansion)',
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text='State name for state-level schemes',
    )
    launch_date = models.DateField(
        null=True,
        blank=True,
        help_text='Official launch / commencement date',
    )
    announced_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date the scheme was announced (may differ from launch)',
    )
    original_objectives = models.TextField(
        blank=True,
        help_text='Original stated objectives at launch',
    )
    intended_beneficiaries = models.TextField(
        blank=True,
        help_text='Description of intended beneficiary population',
    )
    application_portal = models.URLField(
        max_length=500,
        blank=True,
        help_text='Official online application portal URL',
    )
    operational_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UNKNOWN,
    )
    last_researched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When external sources were last retrieved for this scheme',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug'], name='scheme_slug_idx'),
            models.Index(fields=['jurisdiction', 'operational_status'], name='scheme_juris_status_idx'),
            models.Index(fields=['category'], name='scheme_category_idx'),
            models.Index(fields=['country', 'state'], name='scheme_location_idx'),
        ]
        verbose_name = 'Scheme'
        verbose_name_plural = 'Schemes'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:320]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.abbreviation:
            return f'{self.name} ({self.abbreviation})'
        return self.name


class SchemeAlias(models.Model):
    """Scheme alternate names."""

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    alias = models.CharField(
        max_length=300,
        help_text='Alternative name or abbreviation',
    )
    alias_type = models.CharField(
        max_length=50,
        choices=[
            ('abbreviation', 'Abbreviation'),
            ('former_name', 'Former Name'),
            ('translation', 'Translation'),
            ('colloquial', 'Colloquial Name'),
        ],
        default='abbreviation',
    )

    class Meta:
        unique_together = ('scheme', 'alias')
        verbose_name = 'Scheme Alias'
        verbose_name_plural = 'Scheme Aliases'

    def __str__(self) -> str:
        return f'{self.alias} → {self.scheme.name}'


class SchemeBenefit(models.Model):
    """Scheme benefit details."""

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.CASCADE,
        related_name='benefits',
    )
    benefit_type = models.CharField(
        max_length=100,
        help_text='Type of benefit (e.g. financial support, food grain, health cover)',
    )
    description = models.TextField(
        help_text='Full description of the benefit',
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monetary amount, if applicable',
    )
    currency = models.CharField(max_length=10, default='INR', blank=True)
    effective_from = models.DateField(
        null=True,
        blank=True,
        help_text='Date from which this benefit became effective',
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Date until which this benefit was valid (null = still active)',
    )
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='scheme_benefits',
    )

    class Meta:
        ordering = ['scheme', 'effective_from']
        verbose_name = 'Scheme Benefit'
        verbose_name_plural = 'Scheme Benefits'

    def __str__(self) -> str:
        return f'{self.scheme.name} — {self.benefit_type}'


class EligibilityRule(models.Model):
    """Scheme eligibility rule."""

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.CASCADE,
        related_name='eligibility_rules',
    )
    criterion = models.CharField(
        max_length=200,
        help_text='Short label for the eligibility criterion',
    )
    description = models.TextField(
        help_text='Detailed eligibility description',
    )
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='eligibility_rules',
    )

    class Meta:
        ordering = ['scheme', 'effective_from']
        verbose_name = 'Eligibility Rule'
        verbose_name_plural = 'Eligibility Rules'

    def __str__(self) -> str:
        return f'{self.scheme.name} — {self.criterion}'
