"""Admin interface for the sources app."""

from django.contrib import admin

from .models import Source, EvidenceExcerpt


class EvidenceExcerptInline(admin.StackedInline):
    model = EvidenceExcerpt
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'publisher', 'source_category', 'reliability', 'published_date', 'retrieved_at')
    list_filter = ('source_category', 'reliability')
    search_fields = ('title', 'url', 'publisher')
    readonly_fields = ('content_hash', 'created_at', 'updated_at')
    inlines = [EvidenceExcerptInline]
    filter_horizontal = ('schemes',)


@admin.register(EvidenceExcerpt)
class EvidenceExcerptAdmin(admin.ModelAdmin):
    list_display = ('source', 'scheme', 'page_or_section', 'created_at')
    search_fields = ('text', 'source__title')
    raw_id_fields = ('source', 'scheme')
    readonly_fields = ('created_at',)
