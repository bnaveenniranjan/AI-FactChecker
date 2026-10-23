"""Admin interface for the factcheck app."""

from django.contrib import admin

from .models import Claim, ClaimEvidence, FactCheckResult


class ClaimEvidenceInline(admin.StackedInline):
    model = ClaimEvidence
    extra = 0
    raw_id_fields = ('excerpt', 'source')


class FactCheckResultInline(admin.TabularInline):
    model = FactCheckResult
    extra = 0
    readonly_fields = ('created_at', 'processing_time_ms', 'sources_searched', 'sources_used')


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_text_preview', 'scheme', 'verdict', 'confidence', 'verified_at', 'created_at')
    list_filter = ('verdict', 'confidence')
    search_fields = ('claim_text', 'scheme__name')
    raw_id_fields = ('scheme',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ClaimEvidenceInline, FactCheckResultInline]

    @admin.display(description='Claim')
    def claim_text_preview(self, obj):
        return obj.claim_text[:80] + '…' if len(obj.claim_text) > 80 else obj.claim_text


@admin.register(FactCheckResult)
class FactCheckResultAdmin(admin.ModelAdmin):
    list_display = ('claim', 'ai_model_used', 'sources_searched', 'sources_used', 'processing_time_ms', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('claim',)
