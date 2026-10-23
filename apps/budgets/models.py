"""Budget models."""

from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models


class BudgetRecord(models.Model):
    """Scheme budget record."""

    CATEGORY_CENTRAL_SECTOR = 'central_sector'
    CATEGORY_CENTRALLY_SPONSORED = 'centrally_sponsored'
    CATEGORY_STATE = 'state'
    CATEGORY_OTHER = 'other'

    BUDGET_CATEGORY_CHOICES = [
        (CATEGORY_CENTRAL_SECTOR, 'Central Sector Scheme'),
        (CATEGORY_CENTRALLY_SPONSORED, 'Centrally Sponsored Scheme'),
        (CATEGORY_STATE, 'State Scheme'),
        (CATEGORY_OTHER, 'Other'),
    ]

    UNIT_CRORE = 'crore'
    UNIT_LAKH = 'lakh'
    UNIT_MILLION = 'million'
    UNIT_BILLION = 'billion'
    UNIT_ACTUAL = 'actual'

    AMOUNT_UNIT_CHOICES = [
        (UNIT_CRORE, 'Crore'),
        (UNIT_LAKH, 'Lakh'),
        (UNIT_MILLION, 'Million'),
        (UNIT_BILLION, 'Billion'),
        (UNIT_ACTUAL, 'Actual Amount'),
    ]

    STATUS_VERIFIED = 'verified'
    STATUS_PARTIALLY_VERIFIED = 'partially_verified'
    STATUS_UNVERIFIED = 'unverified'
    STATUS_DISPUTED = 'disputed'

    VERIFICATION_STATUS_CHOICES = [
        (STATUS_VERIFIED, 'Verified from official document'),
        (STATUS_PARTIALLY_VERIFIED, 'Partially Verified'),
        (STATUS_UNVERIFIED, 'Unverified'),
        (STATUS_DISPUTED, 'Disputed — sources disagree'),
    ]

    id = models.BigAutoField(primary_key=True)
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.CASCADE,
        related_name='budget_records',
        help_text='Scheme associated with this budget line',
    )
    financial_year_start = models.PositiveIntegerField(
        help_text='Starting calendar year of the financial year (e.g. 2024)',
    )
    financial_year_end = models.PositiveIntegerField(
        help_text='Ending calendar year of the financial year (e.g. 2025)',
    )
    budget_category = models.CharField(
        max_length=30,
        choices=BUDGET_CATEGORY_CHOICES,
        default=CATEGORY_CENTRAL_SECTOR,
        help_text='Classification of scheme funding model',
    )
    budget_estimate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Budget Estimate (BE) allocated at the beginning of the financial year',
    )
    revised_estimate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Revised Estimate (RE) updated mid-year',
    )
    actual_expenditure = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual expenditure realized at year-end',
    )
    central_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Central government contribution portion',
    )
    state_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='State government contribution portion',
    )
    currency = models.CharField(
        max_length=10,
        default='INR',
        help_text='Currency denomination (default INR)',
    )
    amount_unit = models.CharField(
        max_length=20,
        choices=AMOUNT_UNIT_CHOICES,
        default=UNIT_CRORE,
        help_text='Unit scale of recorded amounts (e.g. crore, lakh)',
    )
    budget_head = models.CharField(
        max_length=200,
        blank=True,
        help_text='Official budget head number or accounting code',
    )
    source = models.ForeignKey(
        'sources.Source',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='budget_records',
        help_text='Primary documentation source verifying this budget record',
    )
    notes = models.TextField(
        blank=True,
        help_text='Explanatory notes, footnotes, or variances',
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=STATUS_UNVERIFIED,
        help_text='Fact-checking verification status',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheme', 'financial_year_start']
        unique_together = ('scheme', 'financial_year_start', 'financial_year_end', 'budget_category')
        indexes = [
            models.Index(fields=['scheme', 'financial_year_start'], name='budget_scheme_fy_idx'),
            models.Index(fields=['verification_status'], name='budget_verif_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(financial_year_end=models.F('financial_year_start') + 1),
                name='check_fy_end_is_start_plus_one',
            ),
            models.CheckConstraint(
                condition=models.Q(budget_estimate__isnull=True) | models.Q(budget_estimate__gte=0),
                name='check_budget_estimate_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(revised_estimate__isnull=True) | models.Q(revised_estimate__gte=0),
                name='check_revised_estimate_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(actual_expenditure__isnull=True) | models.Q(actual_expenditure__gte=0),
                name='check_actual_expenditure_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(central_share__isnull=True) | models.Q(central_share__gte=0),
                name='check_central_share_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(state_share__isnull=True) | models.Q(state_share__gte=0),
                name='check_state_share_non_negative',
            ),
        ]
        verbose_name = 'Budget Record'
        verbose_name_plural = 'Budget Records'

    def clean(self):
        super().clean()
        errors = {}

        if self.financial_year_start and self.financial_year_end:
            if self.financial_year_end != self.financial_year_start + 1:
                errors['financial_year_end'] = (
                    f'Financial year end ({self.financial_year_end}) must be exactly one year '
                    f'after start year ({self.financial_year_start}), e.g., {self.financial_year_start}-{self.financial_year_start + 1}.'
                )

        if self.budget_estimate is not None and self.budget_estimate < Decimal('0'):
            errors['budget_estimate'] = 'Budget estimate cannot be negative.'

        if self.revised_estimate is not None and self.revised_estimate < Decimal('0'):
            errors['revised_estimate'] = 'Revised estimate cannot be negative.'

        if self.actual_expenditure is not None and self.actual_expenditure < Decimal('0'):
            errors['actual_expenditure'] = 'Actual expenditure cannot be negative.'

        if self.central_share is not None and self.central_share < Decimal('0'):
            errors['central_share'] = 'Central share cannot be negative.'

        if self.state_share is not None and self.state_share < Decimal('0'):
            errors['state_share'] = 'State share cannot be negative.'

        if errors:
            raise ValidationError(errors)

    @property
    def financial_year_display(self) -> str:
        """Get financial year text."""
        if self.financial_year_start and self.financial_year_end:
            return f'{self.financial_year_start}-{str(self.financial_year_end)[-2:]}'
        return ''

    @property
    def yoy_change_info(self) -> Optional[dict]:
        """Get year change info."""
        return None

    def __str__(self) -> str:
        scheme_name = self.scheme.name if self.scheme_id else 'Unknown Scheme'
        return f'{scheme_name} — FY {self.financial_year_start}-{str(self.financial_year_end)[-2:]}'
