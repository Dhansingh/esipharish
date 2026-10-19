from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Application, ApplicationFieldValue,
    ApplicationDocument, ApplicationAction,
)


class ApplicationFieldValueInline(admin.TabularInline):
    model = ApplicationFieldValue
    extra = 0
    autocomplete_fields = ("field",)
    fields = ("field", "value")


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    autocomplete_fields = ("requirement",)
    fields = ("requirement", "file", "verified", "verified_by", "verified_at")
    readonly_fields = ("verified_at",)


class ApplicationActionInline(admin.TabularInline):
    model = ApplicationAction
    extra = 0
    fields = ("action", "acted_by", "remarks", "acted_at")
    readonly_fields = ("acted_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "application_no", "applicant_name", "service",
        "status_badge", "submitted_at", "action_buttons",
    )
    list_filter = ("status", "service__institution", "service")
    search_fields = (
        "application_no", "applicant_name",
        "applicant_phone", "applicant_email",
    )
    autocomplete_fields = ("service", "student")
    readonly_fields = ("application_no", "submitted_at", "completed_at")
    inlines = [
        ApplicationFieldValueInline,
        ApplicationDocumentInline,
        ApplicationActionInline,
    ]
    fieldsets = (
        ("Application", {
            "fields": ("application_no", "service", "status", "remarks")
        }),
        ("Applicant", {
            "fields": (
                "applicant_name", "applicant_phone",
                "applicant_email", "applicant_address",
            )
        }),
        ("Submission", {
            "fields": ("submitted_by", "submitted_at", "completed_at", "student")
        }),
    )

    def status_badge(self, obj):
        colors = {
            "draft": "#6c757d",
            "submitted": "#0d6efd",
            "under_review": "#fd7e14",
            "approved": "#198754",
            "rejected": "#dc3545",
            "returned": "#ffc107",
            "completed": "#20c997",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def action_buttons(self, obj):
        if not obj.pk:
            return "—"
        gen_url = reverse("letters:generate_for_application", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank">📄 Generate Letter</a>',
            gen_url,
        )
    action_buttons.short_description = "Letter"


@admin.register(ApplicationFieldValue)
class ApplicationFieldValueAdmin(admin.ModelAdmin):
    list_display = ("application", "field", "value")
    search_fields = ("application__application_no", "field__label", "value")
    autocomplete_fields = ("application", "field")


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ("application", "requirement", "verified", "uploaded_at")
    list_filter = ("verified", "requirement")
    search_fields = ("application__application_no",)
    autocomplete_fields = ("application", "requirement")


@admin.register(ApplicationAction)
class ApplicationActionAdmin(admin.ModelAdmin):
    list_display = ("application", "action", "acted_by", "acted_at")
    list_filter = ("action",)
    search_fields = ("application__application_no", "remarks")
    autocomplete_fields = ("application",)