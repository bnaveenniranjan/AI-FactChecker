"""Tests for the budgets app."""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from apps.schemes.models import Scheme
from apps.budgets.models import BudgetRecord


@pytest.fixture
def scheme(db):
    return Scheme.objects.create(name='Ayushman Bharat PMJAY', abbreviation='PMJAY')


@pytest.mark.django_db
class TestBudgetRecordModel:
    """Test BudgetRecord creation, validation, and financial year display."""

    def _make_record(self, scheme, fy_start=2023, **kwargs):
        defaults = {
            'financial_year_start': fy_start,
            'financial_year_end': fy_start + 1,
            'budget_estimate': Decimal('7200.00'),
            'amount_unit': BudgetRecord.UNIT_CRORE,
        }
        defaults.update(kwargs)
        return BudgetRecord.objects.create(scheme=scheme, **defaults)

    def test_budget_record_created(self, scheme):
        record = self._make_record(scheme)
        assert record.pk is not None
        assert record.scheme == scheme

    def test_financial_year_display(self, scheme):
        record = self._make_record(scheme, fy_start=2024)
        assert record.financial_year_display == '2024-25'

    def test_financial_year_display_2019(self, scheme):
        record = self._make_record(scheme, fy_start=2019)
        assert record.financial_year_display == '2019-20'

    def test_invalid_financial_year_end_raises(self, scheme):
        """financial_year_end must be exactly start + 1."""
        record = BudgetRecord(
            scheme=scheme,
            financial_year_start=2023,
            financial_year_end=2025,  # wrong — should be 2024
            budget_estimate=Decimal('1000'),
        )
        with pytest.raises(ValidationError) as exc_info:
            record.clean()
        assert 'financial_year_end' in exc_info.value.message_dict

    def test_negative_budget_estimate_raises(self, scheme):
        record = BudgetRecord(
            scheme=scheme,
            financial_year_start=2023,
            financial_year_end=2024,
            budget_estimate=Decimal('-100'),
        )
        with pytest.raises(ValidationError) as exc_info:
            record.clean()
        assert 'budget_estimate' in exc_info.value.message_dict

    def test_null_values_allowed(self, scheme):
        """BE, RE, and actual can all be null — they are separate fields."""
        record = self._make_record(
            scheme,
            budget_estimate=None,
            revised_estimate=None,
            actual_expenditure=None,
        )
        assert record.budget_estimate is None
        assert record.revised_estimate is None
        assert record.actual_expenditure is None

    def test_be_re_actuals_are_separate(self, scheme):
        """Confirm all three fields are stored independently."""
        record = self._make_record(
            scheme,
            budget_estimate=Decimal('7200.00'),
            revised_estimate=Decimal('6800.00'),
            actual_expenditure=Decimal('6500.00'),
        )
        assert record.budget_estimate == Decimal('7200.00')
        assert record.revised_estimate == Decimal('6800.00')
        assert record.actual_expenditure == Decimal('6500.00')

    def test_unique_together_constraint(self, scheme):
        """Cannot have two records for the same scheme + FY + category."""
        self._make_record(scheme, fy_start=2023, budget_category=BudgetRecord.CATEGORY_CENTRAL_SECTOR)
        with pytest.raises(Exception):
            self._make_record(scheme, fy_start=2023, budget_category=BudgetRecord.CATEGORY_CENTRAL_SECTOR)

    def test_str_representation(self, scheme):
        record = self._make_record(scheme, fy_start=2022)
        assert 'Ayushman Bharat' in str(record)
        assert '2022' in str(record)

    def test_verification_status_defaults_unverified(self, scheme):
        record = self._make_record(scheme)
        assert record.verification_status == BudgetRecord.STATUS_UNVERIFIED
