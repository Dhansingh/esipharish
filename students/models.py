from django.db import models

# Create your models here.
from django.db import models
from institutions.models import Institution, Department


class AcademicYear(models.Model):
    """
    Example: 2082/83 BS or 2025/26 AD
    """
    name = models.CharField(max_length=20, unique=True)  # e.g. "2082/2083"
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Only one current academic year
        if self.is_current:
            AcademicYear.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Program(models.Model):
    """
    Example: BBS, BSc CSIT, BA, +2 Management
    """
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="programs"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="programs"
    )

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, blank=True)
    duration_years = models.PositiveIntegerField(default=4)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["institution", "name"]
        unique_together = ("institution", "name")

    def __str__(self):
        return f"{self.name} ({self.institution})"


class Student(models.Model):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="students"
    )

    # Core fields
    full_name = models.CharField(max_length=200)
    full_name_nepali = models.CharField(max_length=200, blank=True)
    student_id = models.CharField(max_length=50, unique=True)

    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, default="male"
    )
    date_of_birth = models.DateField(blank=True, null=True)

    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=100, blank=True)

    # Family
    father_name = models.CharField(max_length=200, blank=True)
    mother_name = models.CharField(max_length=200, blank=True)
    guardian_name = models.CharField(max_length=200, blank=True)

    # Citizenship / ID
    citizenship_no = models.CharField(max_length=50, blank=True)

    photo = models.ImageField(
        upload_to="students/photos/", blank=True, null=True
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class Enrollment(models.Model):
    """
    Links a Student to a Program + AcademicYear + Semester/Year.
    """
    STATUS_CHOICES = [
        ("active", "Active"),
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("left", "Left"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="enrollments"
    )
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="enrollments"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="enrollments"
    )

    semester_or_year = models.CharField(max_length=20, blank=True)  # e.g. "2nd Year"
    roll_no = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="active"
    )
    enrolled_on = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-academic_year", "student"]
        unique_together = ("student", "program", "academic_year")

    def __str__(self):
        return f"{self.student.full_name} — {self.program.name} ({self.academic_year.name})"