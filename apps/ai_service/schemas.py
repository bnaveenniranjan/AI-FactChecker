"""
Pydantic schemas for structured Gemini AI output.

These schemas are the contract between Gemini's JSON output
and our application's data layer. Gemini must receive retrieved
evidence as context and must NOT invent sources or fill missing
data with guesses.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class VerificationStatus(str, Enum):
    VERIFIED = 'verified'
    PARTIALLY_VERIFIED = 'partially_verified'
    UNVERIFIED = 'unverified'
    DISPUTED = 'disputed'


class ClaimVerdict(str, Enum):
    SUPPORTED = 'supported'
    CONTRADICTED = 'contradicted'
    PARTIALLY_SUPPORTED = 'partially_supported'
    INSUFFICIENT_EVIDENCE = 'insufficient_evidence'
    OUTDATED = 'outdated'


class ConfidenceLevel(str, Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


# ---------------------------------------------------------------------------
# Scheme Overview Schema
# ---------------------------------------------------------------------------

class SchemeOverviewSchema(BaseModel):
    """Structured output for scheme overview extracted from sources."""

    name: str = Field(..., description='Official full name of the scheme')
    abbreviation: Optional[str] = Field(None, description='Common abbreviation, e.g. PM-KISAN')
    category: Optional[str] = None
    jurisdiction: Optional[str] = Field(None, description='central / state / joint')
    country: str = Field(default='India')
    state: Optional[str] = None
    launch_date: Optional[str] = Field(None, description='ISO date string YYYY-MM-DD or null if unknown')
    original_objectives: Optional[str] = None
    intended_beneficiaries: Optional[str] = None
    application_portal: Optional[str] = None
    operational_status: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    data_gaps: List[str] = Field(
        default_factory=list,
        description='List of fields where data was unavailable in retrieved sources',
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description='URLs of sources used to populate this overview',
    )


# ---------------------------------------------------------------------------
# Budget Record Schema
# ---------------------------------------------------------------------------

class BudgetRecordSchema(BaseModel):
    """Structured output for a single financial year budget entry."""

    financial_year: str = Field(..., description='Financial year, e.g. "2023-24"')
    budget_estimate: Optional[float] = Field(None, description='Budget Estimate (BE)')
    revised_estimate: Optional[float] = Field(None, description='Revised Estimate (RE)')
    actual_expenditure: Optional[float] = Field(None, description='Actual expenditure')
    amount_unit: str = Field(default='crore', description='Unit: crore / lakh / million / actual')
    currency: str = Field(default='INR')
    central_share: Optional[float] = None
    state_share: Optional[float] = None
    budget_head: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    data_gaps: List[str] = Field(default_factory=list)

    @field_validator('financial_year')
    @classmethod
    def validate_financial_year(cls, v: str) -> str:
        """Ensure financial year is in expected format like 2023-24."""
        if not v or len(v) < 4:
            raise ValueError(f'Invalid financial year format: {v!r}')
        return v


# ---------------------------------------------------------------------------
# Timeline Event Schema
# ---------------------------------------------------------------------------

class TimelineEventSchema(BaseModel):
    """Structured output for a single chronological scheme event."""

    event_type: str = Field(
        ...,
        description='One of: launch, amendment, budget_update, eligibility_change, leadership_change, suspension, revival, merger, evaluation_report, other',
    )
    title: str = Field(..., description='Short human-readable title')
    description: str = Field(..., description='Detailed description of the event')
    event_date: Optional[str] = Field(None, description='ISO date YYYY-MM-DD or null if unknown')
    announced_date: Optional[str] = None
    responsible_ministry: Optional[str] = None
    responsible_leader: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source_urls: List[str] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Amendment Schema
# ---------------------------------------------------------------------------

class AmendmentSchema(BaseModel):
    """Structured output for a scheme amendment."""

    title: str
    effective_date: Optional[str] = None
    announced_date: Optional[str] = None
    previous_provision: Optional[str] = None
    new_provision: Optional[str] = None
    official_reason: Optional[str] = Field(
        None,
        description='Officially stated reason from government records only',
    )
    independent_analysis: Optional[str] = Field(
        None,
        description='Independent or expert analysis — must be clearly distinguished from official reason',
    )
    beneficiaries_affected: Optional[str] = None
    budgetary_implication: Optional[str] = None
    decision_authority: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source_urls: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Leadership Record Schema
# ---------------------------------------------------------------------------

class LeadershipRecordSchema(BaseModel):
    """Historical leadership record for a scheme during a specific period."""

    leader_name: Optional[str] = None
    role: Optional[str] = None
    party: Optional[str] = None
    government_name: Optional[str] = None
    coalition: Optional[str] = None
    ministry: Optional[str] = None
    portfolio: Optional[str] = None
    tenure_start: Optional[str] = None
    tenure_end: Optional[str] = None
    responsibility_type: Optional[str] = Field(
        None,
        description='One of: launch, administration, amendment',
    )
    source_urls: List[str] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Fact Check Verdict Schema
# ---------------------------------------------------------------------------

class EvidenceItemSchema(BaseModel):
    """A single piece of evidence for or against a claim."""

    text: str = Field(..., description='Exact excerpt from the source')
    source_url: str
    source_title: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    event_date: Optional[str] = None
    stance: str = Field(
        ...,
        description='One of: supports, contradicts, neutral',
    )


class FactCheckVerdictSchema(BaseModel):
    """Complete fact-check verdict for a single claim."""

    original_claim: str
    verdict: ClaimVerdict
    explanation: str = Field(
        ...,
        description='Short, transparent explanation of the verdict',
    )
    supporting_evidence: List[EvidenceItemSchema] = Field(default_factory=list)
    contradicting_evidence: List[EvidenceItemSchema] = Field(default_factory=list)
    confidence: ConfidenceLevel
    confidence_explanation: str
    verified_at: Optional[str] = None
    data_gaps: List[str] = Field(
        default_factory=list,
        description='What information was missing or unavailable',
    )


# ---------------------------------------------------------------------------
# Research Result Schema — top-level container
# ---------------------------------------------------------------------------

class ResearchResultSchema(BaseModel):
    """Full structured research result for a scheme query."""

    query: str
    scheme_name: Optional[str] = None
    overview: Optional[SchemeOverviewSchema] = None
    timeline_events: List[TimelineEventSchema] = Field(default_factory=list)
    amendments: List[AmendmentSchema] = Field(default_factory=list)
    budget_records: List[BudgetRecordSchema] = Field(default_factory=list)
    leadership_records: List[LeadershipRecordSchema] = Field(default_factory=list)
    source_urls_searched: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    data_gaps: List[str] = Field(default_factory=list)
    ai_model_used: Optional[str] = None
