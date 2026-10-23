"""Admin interface for the leadership app."""

from django.contrib import admin

from .models import (
    PoliticalParty, Government, Leader,
    MinistryOrDepartment, MinisterialTenure, SchemeResponsibility,
)


@admin.register(PoliticalParty)
class PoliticalPartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'country', 'founded_year')
    search_fields = ('name', 'abbreviation')


@admin.register(Government)
class GovernmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'country', 'state', 'ruling_party', 'term_start', 'term_end')
    list_filter = ('level', 'country')
    search_fields = ('name', 'coalition_name')
    raw_id_fields = ('ruling_party', 'source')


@admin.register(Leader)
class LeaderAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'party', 'birth_year')
    search_fields = ('full_name',)
    raw_id_fields = ('party',)


@admin.register(MinistryOrDepartment)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'government', 'effective_from', 'effective_to')
    search_fields = ('name', 'abbreviation')
    raw_id_fields = ('government', 'parent_ministry')


@admin.register(MinisterialTenure)
class MinisterialTenureAdmin(admin.ModelAdmin):
    list_display = ('leader', 'role', 'ministry', 'government', 'tenure_start', 'tenure_end')
    list_filter = ('role',)
    search_fields = ('leader__full_name', 'portfolio')
    raw_id_fields = ('leader', 'ministry', 'government', 'source')


@admin.register(SchemeResponsibility)
class SchemeResponsibilityAdmin(admin.ModelAdmin):
    list_display = ('scheme', 'responsibility_type', 'ministry', 'effective_from', 'effective_to')
    list_filter = ('responsibility_type',)
    raw_id_fields = ('scheme', 'ministerial_tenure', 'ministry', 'source')
