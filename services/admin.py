from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Service, ServiceField, DocumentRequirement


class ServiceFieldInline(admin.TabularInline):
    model = ServiceField
    extra = 0
    fields = (
        "order", "label", "field_key", "field_type",
        "required", "placeholder", "choices_text", "active",
    )
    ordering = ("order",)


class DocumentRequirementInline(admin.TabularInline):
    model = DocumentRequirement
    extra = 0
    fields = ("order", "name", "required", "active")
    ordering = ("order",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "institution", "department",
        "number_prefix", "last_serial", "active",
    )
    list_filter = ("institution", "department", "active")
    search_fields = ("name", "code")
    autocomplete_fields = ("institution", "department")
    inlines = [ServiceFieldInline, DocumentRequirementInline]
    fieldsets = (
        ("Identity", {
            "fields": ("institution", "department", "name", "code", "description")
        }),
        ("Numbering", {
            "fields": ("number_prefix", "last_serial"),
            "description": "Application numbers use the format: "
                           "&lt;prefix&gt;-&lt;BS year&gt;-&lt;serial&gt;, e.g. SCH-2082-0001",
        }),
        ("Options", {
            "fields": ("requires_documents", "active")
        }),
    )
    readonly_fields = ("last_serial",)


@admin.register(ServiceField)
class ServiceFieldAdmin(admin.ModelAdmin):
    list_display = (
        "service", "order", "label", "field_key",
        "field_type", "required", "active",
    )
    list_filter = ("service", "field_type", "required", "active")
    search_fields = ("label", "field_key", "service__name")
    autocomplete_fields = ("service",)


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ("service", "order", "name", "required", "active")
    list_filter = ("service", "required", "active")
    search_fields = ("name", "service__name")
    autocomplete_fields = ("service",)