from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from services.models import Service, ServiceField, DocumentRequirement
from datetime import date


class Application(models.Model):
    """
    A submitted request for a service. Generic — works for any office.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("returned", "Returned for Correction"),
        ("completed", "Completed"),
    ]

    application_no = models.CharField(
        max_length=50, unique=True, blank=True,
        help_text="Auto-generated on save (per-service serial).",
    )

    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="applications",
    )

    # Applicant core info (mirrors some service fields for quick listing)
    applicant_name = models.CharField(max_length=200)
    applicant_phone = models.CharField(max_length=20, blank=True)
    applicant_email = models.EmailField(blank=True)
    applicant_address = models.CharField(max_length=255, blank=True)

    # Submission
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="submitted_applications",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="submitted",
    )
    remarks = models.TextField(blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    # Link to optional student record (kept for campus use, not required)
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="applications",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.application_no} — {self.applicant_name}"

    def save(self, *args, **kwargs):
        if not self.application_no:
            bs_year = str(date.today().year + 56)  # rough BS year
            self.application_no = self.service.next_application_no(bs_year)
        super().save(*args, **kwargs)

    def get_field_value(self, field_key):
        fv = self.field_values.filter(field__field_key=field_key).first()
        return fv.value if fv else ""

    def field_map(self):
        """Returns dict {field_key: value} — easy for templates."""
        return {
            fv.field.field_key: fv.value
            for fv in self.field_values.select_related("field")
        }


class ApplicationFieldValue(models.Model):
    """
    Stores one dynamic field value for an Application.
    """
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="field_values",
    )
    field = models.ForeignKey(
        ServiceField, on_delete=models.PROTECT, related_name="values",
    )
    value = models.TextField(blank=True)

    class Meta:
        unique_together = ("application", "field")
        ordering = ["field__order"]

    def __str__(self):
        return f"{self.application.application_no} — {self.field.label}"


class ApplicationDocument(models.Model):
    """
    Uploaded document for an Application, linked to a DocumentRequirement.
    """
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="documents",
    )
    requirement = models.ForeignKey(
        DocumentRequirement, on_delete=models.PROTECT, related_name="uploads",
    )
    file = models.FileField(upload_to="applications/%Y/%m/")

    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="verified_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["requirement__order"]

    def __str__(self):
        return f"{self.application.application_no} — {self.requirement.name}"


class ApplicationAction(models.Model):
    """
    Audit log: every status change or note made on an Application.
    """
    ACTION_CHOICES = [
        ("submitted", "Submitted"),
        ("reviewed", "Reviewed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("returned", "Returned"),
        ("note", "Note"),
        ("completed", "Completed"),
    ]

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="actions",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    remarks = models.TextField(blank=True)
    acted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-acted_at"]

    def __str__(self):
        return f"{self.application.application_no} — {self.get_action_display()}"