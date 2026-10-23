"""Budget admin configuration."""

from django.contrib import admin

from .models import BudgetRecord


@admin.register(BudgetRecord)
class BudgetRecordAdmin(admin.ModelAdmin):
    """Budget admin."""

    list_display = (
        'scheme',
        'financial_year_display',
        'budget_estimate',
        'revised_estimate',
        'actual_expenditure',
        'amount_unit',
        'currency',
        'verification_status',
    )
    list_filter = (
        'verification_status',
        'currency',
        'amount_unit',
        'financial_year_start',
    )
    search_fields = (
        'scheme__name',
        'budget_head',
        'notes',
    )
    raw_id_fields = (
        'scheme',
        'source',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    list_per_page = 50
    fieldsets = (
        ('Scheme & Financial Year', {
            'fields': (
                'scheme',
                'budget_category',
                'financial_year_start',
                'financial_year_end',
                'budget_head',
            )
        }),
        ('Allocations & Expenditures', {
            'fields': (
                'budget_estimate',
                'revised_estimate',
                'actual_expenditure',
                'central_share',
                'state_share',
                'currency',
                'amount_unit',
            )
        }),
        ('Verification & Provenance', {
            'fields': (
                'verification_status',
                'source',
                'notes',
                'created_at',
                'updated_at',
            )
        }),
    )

    @admin.display(description='Financial Year', ordering='financial_year_start')
    def financial_year_display(self, obj: BudgetRecord) -> str:
        """Show financial year."""
        return obj.financial_year_display
