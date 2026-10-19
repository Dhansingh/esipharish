from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    LetterPad, LetterPadPosition,
    LetterTemplate, GeneratedLetter,NumberCounter
)
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator

# ─────────────────────────────────────────────
# LetterPad
# ─────────────────────────────────────────────

class LetterPadPositionInline(admin.TabularInline):
    model = LetterPadPosition
    extra = 0
    fields = (
        "field_name", "x", "y", "width", "height",
        "font_size", "font_name", "alignment",
    )
    ordering = ("field_name",)


@admin.register(LetterPad)
class LetterPadAdmin(admin.ModelAdmin):
    list_display = (
        "name", "institution", "is_active",
        "uploaded_at", "edit_positions", "has_preview",
    )
    list_filter = ("institution", "is_active")
    search_fields = ("name", "institution__name")
    autocomplete_fields = ("institution",)
    inlines = [LetterPadPositionInline]
    actions = ["generate_previews"]
    readonly_fields = ("uploaded_at", "updated_at", "page_width", "page_height")

    fieldsets = (
        ("Identity", {
            "fields": ("institution", "name", "is_active")
        }),
        ("File", {
            "fields": ("pdf_file", "preview_image", "page_width", "page_height"),
            "description": "Upload the complete official letter-pad PDF. "
                           "Preview image and page size are auto-generated.",
        }),
        ("Timestamps", {
            "fields": ("uploaded_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.pdf_file and not obj.preview_image:
            try:
                obj.generate_preview_image()
            except Exception as e:
                self.message_user(
                    request,
                    f"Preview generation failed: {e}",
                    level="warning",
                )

    def edit_positions(self, obj):
        if obj.pk:
            url = reverse("letters:editor", args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" target="_blank">🎨 Edit Positions</a>',
                url,
            )
        return "—"
    edit_positions.short_description = "Editor"

    def has_preview(self, obj):
        return bool(obj.preview_image)
    has_preview.boolean = True
    has_preview.short_description = "Preview?"

    @admin.action(description="🖼 Generate preview image from PDF")
    def generate_previews(self, request, queryset):
        ok, fail = 0, 0
        for lp in queryset:
            try:
                lp.generate_preview_image()
                ok += 1
            except Exception as e:
                fail += 1
                self.message_user(request, f"{lp.name}: {e}", level="error")
        self.message_user(
            request,
            f"✅ {ok} preview(s) generated. ❌ {fail} failed.",
        )


@admin.register(LetterPadPosition)
class LetterPadPositionAdmin(admin.ModelAdmin):
    list_display = (
        "letter_pad", "field_name", "x", "y",
        "width", "height", "font_size", "alignment",
    )
    list_filter = ("letter_pad", "field_name")
    search_fields = ("letter_pad__name",)
    autocomplete_fields = ("letter_pad",)


# ─────────────────────────────────────────────
# LetterTemplate
# ─────────────────────────────────────────────

@admin.register(LetterTemplate)
class LetterTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name", "institution", "service",
        "letter_pad", "active", "created_at",
    )
    list_filter = ("institution", "service", "active")
    search_fields = ("name", "code")
    autocomplete_fields = ("institution", "service", "letter_pad")
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Identity", {
            "fields": ("institution", "service", "name", "code")
        }),

        ("Auto Numbering", {
            "description": (
                "च. नं. र पत्र संख्या auto-increment।<br>"
                "Counter हरेक साल (BS) मा १ बाट फेरि सुरु हुन्छ।<br>"
                "Staff ले Create Letter पेजमा मिलाउन सक्छन्।"
            ),
            "fields": (
                "auto_dispatch", "dispatch_start",
                "auto_reference", "reference_format", "reference_start",
            ),
        }),
        ("Letter Pad", {
            "fields": ("letter_pad", "active")
        }),
        ("Dynamic Content (from Application — advanced)", {
            "description": (
                "Used when generating from an Application. "
                "Available: {{ application.* }}, {{ field_map.* }}, {{ today_bs }}"
            ),
            "classes": ("collapse",),
            "fields": (
                "reference_no_template",
                "dispatch_no_template",
                "date_template",
                "recipient_template",
                "subject_template",
                "body_template",
                "signature_template",
            ),
        }),
        ("Editable Fields (for Create Letter page)", {
            "description": (
                "One field per line: <b>key|label|default</b><br>"
                "Valid keys: reference_no, dispatch_no, date, recipient, "
                "subject, body, signature"
            ),
            "fields": ("editable_fields",),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )


# ─────────────────────────────────────────────
# GeneratedLetter
# ─────────────────────────────────────────────

@admin.register(GeneratedLetter)
class GeneratedLetterAdmin(admin.ModelAdmin):
    list_display = (
        "reference_no", "template", "application", "enrollment",
        "generated_by", "generated_at", "download_link",
    )
    list_filter = ("template", "generated_at")
    search_fields = (
        "reference_no", "dispatch_no",
        "application__application_no",
        "enrollment__student__full_name",
    )
    readonly_fields = ("generated_at", "pdf_file", "download_link")
    autocomplete_fields = ("template", "application", "enrollment")

    def download_link(self, obj):
        if obj.pk and obj.pdf_file:
            return format_html(
                '<a class="button" href="{}" target="_blank">📥 Download</a>',
                obj.pdf_file.url,
            )
        return "—"
    download_link.short_description = "Download"
    def regenerate_button(self, obj):
        if not obj.pk:
            return "—"
        url = reverse("letters:regenerate_letter", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank">✏️ Edit & Re-generate</a>',
            url,
        )
    regenerate_button.short_description = "Edit"

    def version_badge(self, obj):
        color = "#f59e0b" if obj.version > 1 else "#10b981"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;">v{}</span>',
            color, obj.version,
        )
    version_badge.short_description = "Ver."

    list_display = (
        "reference_no", "version_badge", "template",
        "application", "enrollment", "generated_by",
        "generated_at", "download_link", "regenerate_button",
    )






@admin.register(NumberCounter)
class NumberCounterAdmin(admin.ModelAdmin):
    list_display = ("institution", "counter_type", "bs_year", "last_number")
    list_filter = ("institution", "counter_type", "bs_year")
    search_fields = ("institution__name", "bs_year")
# ─────────────────────────────────────────────
# Custom links in admin sidebar
# ─────────────────────────────────────────────

from django.contrib import admin as django_admin
from django.urls import reverse
from django.utils.html import format_html


class QuickActionsAdmin(django_admin.ModelAdmin):
    """
    A dummy ModelAdmin that adds quick action buttons to the admin index.
    """
    pass


# Add quick action links to the admin index page
_original_index = django_admin.site.index


def custom_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    extra_context["quick_actions"] = [
        {
            "title": "📄 Create Letter",
            "url": reverse("letters:create_letter"),
            "desc": "कुनै पनि प्रकारको letter वा सिफारिस छाप्नुहोस्",
        },
        {
            "title": "📢 Create Notice",
            "url": reverse("letters:create_notice"),
            "desc": "कार्यालयको सूचना छाप्नुहोस्",
        },
        {
            "title": "📑 Letter History",
            "url": "/admin/letters/generatedletter/",
            "desc": "पहिले छापिएका letters हेर्नुहोस्",
        },
    ]
    return _original_index(request, extra_context=extra_context)


django_admin.site.index = custom_admin_index