from django.db import models

# Create your models here.
from django.db import models
from institutions.models import Institution, Department


class Service(models.Model):
    """
    A service offered by an institution (or its department).
    Examples:
        - Scholarship Sifarish
        - Migration Certificate
        - Ward Recommendation
        - TU Affiliation Letter
        - Character Certificate
        - Exam Notice
    """

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="services",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="services",
    )

    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20,
        help_text="Short code used for numbering. Example: SCH, MIG, WARD",
    )
    description = models.TextField(blank=True)

    # Numbering
    number_prefix = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional override. If blank, uses 'code'.",
    )
    last_serial = models.PositiveIntegerField(
        default=0,
        help_text="Auto-incremented when a new application is created.",
    )

    requires_documents = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["institution", "name"]
        unique_together = ("institution", "code")

    def __str__(self):
        dept = f" / {self.department.name}" if self.department else ""
        return f"{self.name} ({self.institution.short_name or self.institution.name}{dept})"

    def next_application_no(self, bs_year):
        """
        Generate next application number.
        Example: SCH-2082-0001
        """
        prefix = self.number_prefix or self.code or "APP"
        self.last_serial += 1
        self.save(update_fields=["last_serial"])
        return f"{prefix}-{bs_year}-{self.last_serial:04d}"


class ServiceField(models.Model):
    """
    A single dynamic form field for a Service.
    Staff define these in admin; citizens fill them later.
    """

    FIELD_TYPES = [
        ("text", "Text (single line)"),
        ("textarea", "Text (multi-line)"),
        ("number", "Number"),
        ("date", "Date"),
        ("email", "Email"),
        ("phone", "Phone"),
        ("select", "Dropdown"),
        ("checkbox", "Checkbox"),
        ("file", "File upload"),
    ]

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    label = models.CharField(max_length=200)
    field_key = models.CharField(
        max_length=80,
        help_text="Internal key, no spaces. Example: student_name, father_name",
    )
    field_type = models.CharField(
        max_length=20, choices=FIELD_TYPES, default="text"
    )

    required = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=255, blank=True)

    choices_text = models.TextField(
        blank=True,
        help_text="Only for 'Dropdown'. One choice per line.",
    )

    default_value = models.CharField(max_length=255, blank=True)

    order = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["service", "order"]
        unique_together = ("service", "field_key")

    def __str__(self):
        return f"{self.service.code} → {self.label}"

    def choices_list(self):
        return [c.strip() for c in self.choices_text.splitlines() if c.strip()]


class DocumentRequirement(models.Model):
    """
    Documents the applicant must upload for this service.
    Example: Citizenship copy, Transcript, Photo
    """

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="document_requirements",
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["service", "order"]

    def __str__(self):
        return f"{self.service.code} → {self.name}"
