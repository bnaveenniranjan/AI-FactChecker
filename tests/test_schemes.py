"""Tests for the schemes app."""

import pytest
from django.utils.text import slugify

from apps.schemes.models import Scheme, SchemeAlias, SchemeBenefit, EligibilityRule


@pytest.mark.django_db
class TestSchemeModel:
    """Test Scheme model creation, slug generation, and relationships."""

    def _make_scheme(self, name='PM-KISAN', **kwargs):
        return Scheme.objects.create(name=name, **kwargs)

    def test_scheme_created_with_defaults(self):
        scheme = self._make_scheme()
        assert scheme.pk is not None
        assert scheme.country == 'India'
        assert scheme.operational_status == Scheme.STATUS_UNKNOWN
        assert scheme.jurisdiction == Scheme.JURISDICTION_CENTRAL

    def test_slug_auto_generated_from_name(self):
        scheme = self._make_scheme(name='Pradhan Mantri Kisan Samman Nidhi')
        assert scheme.slug == slugify('Pradhan Mantri Kisan Samman Nidhi')

    def test_slug_not_overwritten_if_provided(self):
        scheme = self._make_scheme(name='PM Awas Yojana', slug='pm-awas')
        assert scheme.slug == 'pm-awas'

    def test_str_with_abbreviation(self):
        scheme = self._make_scheme(name='Pradhan Mantri Kisan Samman Nidhi', abbreviation='PM-KISAN')
        assert 'PM-KISAN' in str(scheme)

    def test_str_without_abbreviation(self):
        scheme = self._make_scheme(name='Some Scheme Without Abbr')
        assert 'Some Scheme Without Abbr' in str(scheme)

    def test_unique_name_constraint(self):
        self._make_scheme(name='MGNREGA')
        with pytest.raises(Exception):
            self._make_scheme(name='MGNREGA')

    def test_alias_linked_to_scheme(self):
        scheme = self._make_scheme(name='Mahatma Gandhi NREGS')
        alias = SchemeAlias.objects.create(
            scheme=scheme,
            alias='MGNREGS',
            alias_type='abbreviation',
        )
        assert alias.scheme == scheme
        assert 'MGNREGS' in str(alias)

    def test_benefit_linked_to_scheme(self):
        scheme = self._make_scheme()
        benefit = SchemeBenefit.objects.create(
            scheme=scheme,
            benefit_type='Cash Transfer',
            description='₹6000 per year in 3 instalments',
        )
        assert benefit in scheme.benefits.all()

    def test_eligibility_rule_linked_to_scheme(self):
        scheme = self._make_scheme()
        rule = EligibilityRule.objects.create(
            scheme=scheme,
            criterion='Land Holding',
            description='Small and marginal farmers with cultivable land',
        )
        assert rule in scheme.eligibility_rules.all()

    def test_multiple_categories(self):
        for cat_value, _ in Scheme.CATEGORY_CHOICES:
            scheme = Scheme.objects.create(
                name=f'Test Scheme {cat_value}',
                category=cat_value,
            )
            assert scheme.category == cat_value
