"""API serializers."""

from rest_framework import serializers

from apps.schemes.models import Scheme, SchemeAlias, SchemeBenefit, EligibilityRule
from apps.leadership.models import (
    PoliticalParty, Government, Leader,
    MinistryOrDepartment, MinisterialTenure, SchemeResponsibility,
)
from apps.budgets.models import BudgetRecord
from apps.timeline.models import TimelineEvent, SchemeAmendment
from apps.sources.models import Source, EvidenceExcerpt
from apps.factcheck.models import Claim, ClaimEvidence, FactCheckResult
from apps.search.models import ResearchJob


# Sources
class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            'id', 'title', 'url', 'publisher', 'source_category',
            'published_date', 'retrieved_at', 'reliability',
        ]


class EvidenceExcerptSerializer(serializers.ModelSerializer):
    source = SourceSerializer(read_only=True)

    class Meta:
        model = EvidenceExcerpt
        fields = ['id', 'source', 'text', 'page_or_section', 'created_at']


# Schemes
class SchemeAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemeAlias
        fields = ['id', 'alias', 'alias_type']


class SchemeBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemeBenefit
        fields = [
            'id', 'benefit_type', 'description', 'amount', 'currency',
            'effective_from', 'effective_to',
        ]


class EligibilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EligibilityRule
        fields = ['id', 'criterion', 'description', 'effective_from', 'effective_to']


class SchemeListSerializer(serializers.ModelSerializer):
    """List serializer."""

    class Meta:
        model = Scheme
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'category',
            'jurisdiction', 'country', 'state',
            'operational_status', 'launch_date',
        ]


class SchemeDetailSerializer(serializers.ModelSerializer):
    """Detail serializer."""

    aliases = SchemeAliasSerializer(many=True, read_only=True)
    benefits = SchemeBenefitSerializer(many=True, read_only=True)
    eligibility_rules = EligibilityRuleSerializer(many=True, read_only=True)

    class Meta:
        model = Scheme
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'category',
            'jurisdiction', 'country', 'state',
            'launch_date', 'announced_date',
            'original_objectives', 'intended_beneficiaries',
            'application_portal', 'operational_status',
            'last_researched_at', 'created_at', 'updated_at',
            'aliases', 'benefits', 'eligibility_rules',
        ]


# Leadership

class PoliticalPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticalParty
        fields = ['id', 'name', 'abbreviation', 'country']


class LeaderSerializer(serializers.ModelSerializer):
    party = PoliticalPartySerializer(read_only=True)

    class Meta:
        model = Leader
        fields = ['id', 'full_name', 'party', 'birth_year']


class MinistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MinistryOrDepartment
        fields = ['id', 'name', 'abbreviation', 'effective_from', 'effective_to']


class GovernmentSerializer(serializers.ModelSerializer):
    ruling_party = PoliticalPartySerializer(read_only=True)

    class Meta:
        model = Government
        fields = [
            'id', 'name', 'level', 'country', 'state',
            'ruling_party', 'coalition_name', 'term_start', 'term_end',
        ]


class MinisterialTenureSerializer(serializers.ModelSerializer):
    leader = LeaderSerializer(read_only=True)
    ministry = MinistrySerializer(read_only=True)
    government = GovernmentSerializer(read_only=True)

    class Meta:
        model = MinisterialTenure
        fields = [
            'id', 'leader', 'ministry', 'government',
            'role', 'portfolio', 'tenure_start', 'tenure_end',
        ]


class SchemeResponsibilitySerializer(serializers.ModelSerializer):
    ministerial_tenure = MinisterialTenureSerializer(read_only=True)
    ministry = MinistrySerializer(read_only=True)

    class Meta:
        model = SchemeResponsibility
        fields = [
            'id', 'responsibility_type', 'ministerial_tenure', 'ministry',
            'effective_from', 'effective_to', 'notes',
        ]


# Budgets
class BudgetRecordSerializer(serializers.ModelSerializer):
    financial_year = serializers.SerializerMethodField()
    source = SourceSerializer(read_only=True)

    class Meta:
        model = BudgetRecord
        fields = [
            'id', 'financial_year', 'financial_year_start', 'financial_year_end',
            'budget_category',
            'budget_estimate', 'revised_estimate', 'actual_expenditure',
            'central_share', 'state_share',
            'currency', 'amount_unit', 'budget_head',
            'verification_status', 'notes', 'source',
        ]

    def get_financial_year(self, obj: BudgetRecord) -> str:
        return obj.financial_year_display


# Timeline
class TimelineEventSerializer(serializers.ModelSerializer):
    sources = SourceSerializer(many=True, read_only=True)
    government = GovernmentSerializer(read_only=True)
    responsible_ministry = MinistrySerializer(read_only=True)
    responsible_leader = LeaderSerializer(read_only=True)
    amendment = serializers.SerializerMethodField()

    class Meta:
        model = TimelineEvent
        fields = [
            'id', 'event_type', 'title', 'description',
            'event_date', 'announced_date',
            'government', 'responsible_ministry', 'responsible_leader',
            'verification_status', 'sources', 'amendment',
            'created_at', 'updated_at',
        ]

    def get_amendment(self, obj: TimelineEvent):
        try:
            return SchemeAmendmentSerializer(obj.amendment).data
        except Exception:
            return None


class SchemeAmendmentSerializer(serializers.ModelSerializer):
    sources = SourceSerializer(many=True, read_only=True)

    class Meta:
        model = SchemeAmendment
        fields = [
            'id', 'title', 'effective_date', 'announced_date',
            'previous_provision', 'new_provision',
            'official_reason', 'independent_analysis',
            'beneficiaries_affected', 'budgetary_implication',
            'decision_authority', 'verification_status', 'sources',
        ]


# Fact check
class ClaimEvidenceSerializer(serializers.ModelSerializer):
    excerpt = EvidenceExcerptSerializer(read_only=True)
    source = SourceSerializer(read_only=True)

    class Meta:
        model = ClaimEvidence
        fields = [
            'id', 'stance', 'excerpt', 'source',
            'relevance_note', 'publication_date', 'event_date',
        ]


class ClaimSerializer(serializers.ModelSerializer):
    evidence_links = ClaimEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = [
            'id', 'claim_text', 'scheme', 'verdict',
            'explanation', 'confidence', 'confidence_explanation',
            'verified_at', 'evidence_links', 'created_at',
        ]


class FactCheckResultSerializer(serializers.ModelSerializer):
    claim = ClaimSerializer(read_only=True)

    class Meta:
        model = FactCheckResult
        fields = [
            'id', 'claim', 'ai_model_used',
            'processing_time_ms', 'sources_searched', 'sources_used',
            'created_at',
        ]


# Research
class ResearchJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchJob
        fields = [
            'id', 'query', 'status', 'scheme',
            'result', 'error_message',
            'sources_found', 'sources_fetched',
            'started_at', 'completed_at', 'created_at',
        ]
        read_only_fields = [
            'status', 'result', 'error_message',
            'sources_found', 'sources_fetched',
            'started_at', 'completed_at', 'created_at',
        ]


class ResearchRequestSerializer(serializers.Serializer):
    """Research request input."""
    query = serializers.CharField(
        max_length=500,
        help_text='Search query for the government scheme',
    )

    def validate_query(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError('Query must be at least 3 characters.')
        return value


class FactCheckRequestSerializer(serializers.Serializer):
    """Fact check request input."""
    claim = serializers.CharField(
        max_length=1000,
        help_text='The factual claim to verify',
    )
    scheme_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Optional scheme ID to scope the search',
    )

    def validate_claim(self, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Claim must be at least 10 characters.')
        return value
