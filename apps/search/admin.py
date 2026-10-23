"""Admin interface for the search app."""

from django.contrib import admin

from .models import ResearchJob, ResearchCache


@admin.register(ResearchJob)
class ResearchJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'query_preview', 'status', 'scheme', 'sources_fetched', 'started_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('query', 'normalized_query')
    raw_id_fields = ('scheme',)
    readonly_fields = ('created_at', 'started_at', 'completed_at')

    @admin.display(description='Query')
    def query_preview(self, obj):
        return obj.query[:80] + '…' if len(obj.query) > 80 else obj.query


@admin.register(ResearchCache)
class ResearchCacheAdmin(admin.ModelAdmin):
    list_display = ('cache_key_preview', 'normalized_query_preview', 'scheme', 'is_fresh', 'expires_at', 'created_at')
    readonly_fields = ('cache_key', 'created_at', 'is_fresh')

    @admin.display(description='Cache Key')
    def cache_key_preview(self, obj):
        return obj.cache_key[:16] + '…'

    @admin.display(description='Query')
    def normalized_query_preview(self, obj):
        return obj.normalized_query[:60] + '…' if len(obj.normalized_query) > 60 else obj.normalized_query

    @admin.display(description='Fresh?', boolean=True)
    def is_fresh(self, obj):
        return obj.is_fresh
