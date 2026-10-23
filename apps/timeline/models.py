"""
Models for the timeline app.

TimelineEvent and SchemeAmendment store the chronological history
of a scheme from announcement to latest verified update.

Design principle: Adding a new event type must NOT require rewriting
the timeline component. Use the event_type field and a JSONB-style
extra_data field for type-specific attributes.
"""

from django.db import models


class TimelineEvent(models.Model):
    """
    A single dated event in a scheme's history.

    Normalized to support any event type. Frontend renders based on event_type.
    All event data must be traced to a source — do not fabricate events.
    """

    EVENT_LAUNCH = 'launch'
    EVENT_AMENDMENT = 'amendment'
    EVENT_BUDGET = 'budget_update'
    EVENT_ELIGIBILITY = 'eligibility_change'
    EVENT_LEADERSHIP = 'leadership_change'
    EVENT_SUSPENSION = 'suspension'
    EVENT_REVIVAL = 'revival'
    EVENT_MERGER = 'merger'
    EVENT_EVALUATION = 'evaluation_report'
    EVENT_OTHER = 'other'

    EVENT_TYPE_CHOICES = [
        (EVENT_LAUNCH, 'Scheme Launch'),
        (EVENT_AMENDMENT, 'Amendment / Policy Change'),
        (EVENT_BUDGET, 'Budget Update'),
        (EVENT_ELIGIBILITY, 'Eligibility / Benefit Change'),
        (EVENT_LEADERSHIP, 'Leadership Change'),
        (EVENT_SUSPENSION, 'Suspension'),
        (EVENT_REVIVAL, 'Revival'),
        (EVENT_MERGER, 'Merger'),
        (EVENT_EVALUATION, 'Evaluation Report'),
        (EVENT_OTHER, 'Other'),
    ]

    VERIFICATION_VERIFIED = 'verified'
    VERIFICATION_PARTIAL = 'partial'
    VERIFICATION_UNVERIFIED = 'unverified'
    VERIFICATION_CHOICES = [
        (VERIFICATION_VERIFIED, 'Verified'),
        (VERIFICATION_PARTIAL, 'Partially verified'),
        (VERIFICATION_UNVERIFIED, 'Unverified'),
    ]

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.CASCADE,
        related_name='timeline_events',
    )
    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        default=EVENT_OTHER,
    )
    title = models.CharField(
        max_length=300,
        help_text='Short human-readable title for the event',
    )
    description = models.TextField(
        help_text='Detailed description of what happened',
    )
    event_date = models.DateField(
        help_text='Date the event occurred or took effect',
    )
    announced_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date the event was announced, if different from event_date',
    )
    government = models.ForeignKey(
        'leadership.Government',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='timeline_events',
    )
    responsible_ministry = models.ForeignKey(
        'leadership.MinistryOrDepartment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='timeline_events',
    )
    responsible_leader = models.ForeignKey(
        'leadership.Leader',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='timeline_events',
        help_text='Documented official responsible — do not assume based on who was in power',
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHOICES,
        default=VERIFICATION_UNVERIFIED,
    )
    sources = models.ManyToManyField(
        'sources.Source',
        blank=True,
        related_name='timeline_events',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheme', 'event_date']
        indexes = [
            models.Index(fields=['scheme', 'event_date'], name='timeline_scheme_date_idx'),
            models.Index(fields=['event_type'], name='timeline_event_type_idx'),
        ]
        verbose_name = 'Timeline Event'
        verbose_name_plural = 'Timeline Events'

    def __str__(self) -> str:
        return f'{self.scheme.name} — {self.event_date}: {self.title}'


class SchemeAmendment(models.Model):
    """
    A specific documented change to a scheme's policy, eligibility, or benefits.

    Preserves old and new provisions for side-by-side comparison.
    Clearly distinguishes official justification from independent analysis.
    """

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.CASCADE,
        related_name='amendments',
    )
    timeline_event = models.OneToOneField(
        TimelineEvent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='amendment',
        help_text='Linked timeline event for this amendment',
    )
    title = models.CharField(max_length=300)
    effective_date = models.DateField()
    announced_date = models.DateField(null=True, blank=True)
    previous_provision = models.TextField(
        blank=True,
        help_text='The provision as it stood before this amendment',
    )
    new_provision = models.TextField(
        help_text='The provision as changed by this amendment',
    )
    official_reason = models.TextField(
        blank=True,
        help_text='Officially stated reason or justification from government records',
    )
    independent_analysis = models.TextField(
        blank=True,
        help_text='Independent or expert analysis — clearly distinguished from official reason',
    )
    beneficiaries_affected = models.TextField(blank=True)
    budgetary_implication = models.TextField(blank=True)
    decision_authority = models.CharField(
        max_length=300,
        blank=True,
        help_text='Ministry, cabinet, or authority that made the decision',
    )
    verification_status = models.CharField(
        max_length=20,
        choices=TimelineEvent.VERIFICATION_CHOICES,
        default=TimelineEvent.VERIFICATION_UNVERIFIED,
    )
    sources = models.ManyToManyField(
        'sources.Source',
        blank=True,
        related_name='amendments',
    )

    class Meta:
        ordering = ['scheme', 'effective_date']
        verbose_name = 'Scheme Amendment'
        verbose_name_plural = 'Scheme Amendments'

    def __str__(self) -> str:
        return f'{self.scheme.name} — Amendment: {self.title} ({self.effective_date})'
