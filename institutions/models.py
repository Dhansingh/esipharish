from django.db import models


class Institution(models.Model):
    INSTITUTION_TYPES = [
        ("school", "School"),
        ("college", "College"),
        ("campus", "Campus"),
        ("university", "University"),
        ("ward", "Ward Office"),
        ("rural_municipality", "Rural Municipality"),
        ("municipality", "Municipality"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=50, unique=True)

    institution_type = models.CharField(
        max_length=30,
        choices=INSTITUTION_TYPES,
        default="campus",
    )

    address = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)

    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    logo = models.ImageField(
        upload_to="institutions/logos/",
        blank=True,
        null=True,
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.short_name or self.name


class Department(models.Model):
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="departments",
    )

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["institution", "name"]
        unique_together = ("institution", "name")

    def __str__(self):
        return f"{self.institution} - {self.name}"