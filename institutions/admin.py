from django.contrib import admin
from .models import Institution, Department


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "short_name",
        "code",
        "institution_type",
        "district",
        "active",
    )
    search_fields = ("name", "short_name", "code", "district")
    list_filter = ("institution_type", "active", "province")
    prepopulated_fields = {}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "institution",
        "active",
    )
    search_fields = ("name", "code")
    list_filter = ("institution", "active")
    autocomplete_fields = ("institution",)