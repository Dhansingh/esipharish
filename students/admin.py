from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import AcademicYear, Program, Student, Enrollment


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)
    search_fields = ("name",)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "department", "active")
    list_filter = ("institution", "department", "active")
    search_fields = ("name", "code")
    autocomplete_fields = ("institution", "department")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "student_id", "institution",
        "gender", "phone", "active",
    )
    list_filter = ("institution", "gender", "active")
    search_fields = ("full_name", "full_name_nepali", "student_id", "phone")
    autocomplete_fields = ("institution",)
    fieldsets = (
        ("Identity", {
            "fields": ("institution", "full_name", "full_name_nepali",
                       "student_id", "gender", "date_of_birth", "photo")
        }),
        ("Contact", {
            "fields": ("phone", "email", "address", "district")
        }),
        ("Family", {
            "fields": ("father_name", "mother_name", "guardian_name")
        }),
        ("Documents", {
            "fields": ("citizenship_no",)
        }),
        ("Status", {
            "fields": ("active",)
        }),
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student", "program", "academic_year",
        "semester_or_year", "roll_no", "status",
    )
    list_filter = ("program", "academic_year", "status")
    search_fields = ("student__full_name", "student__student_id", "roll_no")
    autocomplete_fields = ("student", "program", "academic_year")
