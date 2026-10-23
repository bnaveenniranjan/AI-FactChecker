"""Admin interface for the schemes app."""

from django.contrib import admin

from .models import Scheme, SchemeAlias, SchemeBenefit, EligibilityRule


class SchemeAliasInline(admin.TabularInline):
    model = SchemeAlias
    extra = 1


class SchemeBenefitInline(admin.StackedInline):
    model = SchemeBenefit
    extra = 0
    show_change_link = True


class EligibilityRuleInline(admin.TabularInline):
    model = EligibilityRule
    extra = 0
    show_change_link = True


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'category', 'jurisdiction', 'country', 'state', 'operational_status', 'launch_date', 'last_researched_at')
    list_filter = ('jurisdiction', 'operational_status', 'category', 'country')
    search_fields = ('name', 'abbreviation', 'aliases__alias')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'last_researched_at')
    inlines = [SchemeAliasInline, SchemeBenefitInline, EligibilityRuleInline]
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'slug', 'abbreviation', 'category', 'jurisdiction', 'country', 'state'),
        }),
        ('Timeline', {
            'fields': ('announced_date', 'launch_date', 'operational_status'),
        }),
        ('Description', {
            'fields': ('original_objectives', 'intended_beneficiaries', 'application_portal'),
        }),
        ('Metadata', {
            'fields': ('last_researched_at', 'created_at', 'updated_at'),
        }),
    )
