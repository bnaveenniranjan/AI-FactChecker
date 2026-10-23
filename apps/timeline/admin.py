"""Admin interface for the timeline app."""

from django.contrib import admin

from .models import TimelineEvent, SchemeAmendment


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'event_type', 'event_date', 'title', 'verification_status')
    list_filter = ('event_type', 'verification_status')
    search_fields = ('scheme__name', 'title', 'description')
    raw_id_fields = ('scheme', 'government', 'responsible_ministry', 'responsible_leader')
    filter_horizontal = ('sources',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'event_date'


@admin.register(SchemeAmendment)
class SchemeAmendmentAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'title', 'effective_date', 'announced_date', 'verification_status')
    list_filter = ('verification_status',)
    search_fields = ('scheme__name', 'title', 'decision_authority')
    raw_id_fields = ('scheme', 'timeline_event')
    filter_horizontal = ('sources',)
    date_hierarchy = 'effective_date'
