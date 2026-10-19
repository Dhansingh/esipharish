from django.db import models
from django.conf import settings
from institutions.models import Institution
from tinymce.models import HTMLField

# ─────────────────────────────────────────────
# LetterPad
# ─────────────────────────────────────────────

class LetterPad(models.Model):
    """
    Admin uploads the complete official letter-pad PDF here.
    This PDF is used as the background. We never modify it —
    we only overlay dynamic text on top.
    """

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="letter_pads",
    )

    name = models.CharField(
        max_length=150,
        help_text="Example: Ghodaghodi Campus Official Letter Pad",
    )

    pdf_file = models.FileField(
        upload_to="letter_pads/pdf/",
        help_text="Upload the complete official letter-pad PDF.",
    )

    preview_image = models.ImageField(
        upload_to="letter_pads/preview/",
        blank=True,
        null=True,
        help_text="Optional PNG/JPG preview of first page (auto-generated).",
    )

    page_width = models.FloatField(
        default=595.0,
        help_text="PDF page width in points (A4 = 595).",
    )
    page_height = models.FloatField(
        default=842.0,
        help_text="PDF page height in points (A4 = 842).",
    )

    is_active = models.BooleanField(default=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.institution} — {self.name}"

    def generate_preview_image(self, dpi=100):
        """Convert first page of the PDF to a PNG preview."""
        from pdf2image import convert_from_path
        from django.core.files.base import ContentFile
        import io

        if not self.pdf_file:
            return

        pages = convert_from_path(
            self.pdf_file.path,
            dpi=dpi,
            first_page=1,
            last_page=1,
        )
        if not pages:
            return

        img = pages[0]
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"letterpad_{self.pk}_preview.png"
        self.preview_image.save(filename, ContentFile(buffer.read()), save=False)

        self.page_width = img.width * 72.0 / dpi
        self.page_height = img.height * 72.0 / dpi
        self.save(update_fields=[
            "preview_image", "page_width", "page_height",
        ])


# ─────────────────────────────────────────────
# LetterPadPosition
# ─────────────────────────────────────────────

class LetterPadPosition(models.Model):
    """
    Where each dynamic field goes on the letter pad.
    Coordinates are in PDF points (origin = bottom-left of page).
    """

    FIELD_CHOICES = [
        ("reference_no", "पत्र संख्या / Reference No."),
        ("dispatch_no", "च. नं. / Dispatch No."),
        ("date", "मिति / Date"),
        ("recipient", "To / Recipient"),
        ("subject", "विषय / Subject"),
        ("body", "Body Content"),
        ("signature", "Signature / Designation"),
    ]

    letter_pad = models.ForeignKey(
        LetterPad,
        on_delete=models.CASCADE,
        related_name="positions",
    )

    field_name = models.CharField(max_length=30, choices=FIELD_CHOICES)

    x = models.FloatField(help_text="X coordinate (from left, in points)")
    y = models.FloatField(help_text="Y coordinate (from bottom, in points)")

    width = models.FloatField(
        default=200.0,
        help_text="Field width for wrapping (body only).",
    )
    height = models.FloatField(
        default=20.0,
        help_text="Field height for wrapping (body only).",
    )

    font_size = models.PositiveIntegerField(default=12)
    font_name = models.CharField(
        max_length=50,
        default="Helvetica",
        help_text="ReportLab font name (Helvetica, Times-Roman, etc.)",
    )

    alignment = models.CharField(
        max_length=10,
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
    )

    class Meta:
        unique_together = ("letter_pad", "field_name")
        ordering = ["letter_pad", "field_name"]

    def __str__(self):
        return f"{self.letter_pad.name} — {self.get_field_name_display()}"


# ─────────────────────────────────────────────
# LetterTemplate
# ─────────────────────────────────────────────

class LetterTemplate(models.Model):
    """
    Defines which dynamic fields get filled and where the values come from.
    Bound to a Service (generic — works for any office).
    """
    
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="letter_templates",
    )

    service = models.ForeignKey(
        "services.Service",
        on_delete=models.CASCADE,
        related_name="letter_templates",
        null=True,
        blank=True,
        help_text="If set, this template is only offered for this service.",
    )

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)

    letter_pad = models.ForeignKey(
        LetterPad,
        on_delete=models.PROTECT,
        related_name="templates",
    )

    reference_no_template = models.CharField(
        max_length=255, blank=True,
        help_text="Example: {{ application.application_no }}",
    )
    dispatch_no_template = models.CharField(
        max_length=255, blank=True,
        help_text="Leave blank to auto-number.",
    )
    date_template = models.CharField(
        max_length=255, blank=True,
        default="{{ today_bs }}",
    )
    recipient_template = models.HTMLField(
        blank=True,
        help_text="Example: श्री {{ field_map.student_name }}\n{{ field_map.address }}",
    )
    subject_template = models.HTMLField(
        max_length=255, blank=True,
    )
    body_template = models.HTMLField(
        blank=True,
        help_text="Use {{ application.* }}, {{ field_map.* }}, {{ service.* }}, {{ today_bs }}",
    )
    signature_template = models.CharField(
        max_length=255, blank=True,
        default="क्याम्पस प्रमुख",
    )
    auto_dispatch = models.BooleanField(default=True)
    dispatch_start = models.PositiveIntegerField(
        default=1,
        help_text="नयाँ सालमा सुरु हुने नम्बर",
    )

    auto_reference = models.BooleanField(default=True)
    reference_format = models.CharField(
        max_length=100,
        blank=True,
        default="{serial:03d}/{year_bs}/{year_bs_next}",
        help_text=(
            "{serial} = बढ्ने नम्बर, {year_bs} = साल, "
            "{year_bs_next} = साल+१, {month_bs} = महिना"
        ),
    )
    reference_start = models.PositiveIntegerField(default=1)
    def preview_dispatch_no(self):
        """अझै increment नगरी अर्को नम्बर देखाउँछ (staff ले edit गर्न सकोस्)।"""
        from .renderer import today_bs_approx
        from .models import NumberCounter
        bs_year = today_bs_approx().split("/")[0]

        obj = NumberCounter.objects.filter(
            institution=self.institution,
            counter_type="dispatch",
            bs_year=bs_year,
        ).first()

        if not obj:
            return self.dispatch_start
        return obj.last_number + 1

    def preview_reference_no(self):
        """अझै increment नगरी अर्को reference देखाउँछ।"""
        from .renderer import today_bs_approx
        from .models import NumberCounter
        bs = today_bs_approx()
        bs_year = bs.split("/")[0]
        bs_month = bs.split("/")[1]

        obj = NumberCounter.objects.filter(
            institution=self.institution,
            counter_type="reference",
            bs_year=bs_year,
        ).first()

        serial = (obj.last_number + 1) if obj else self.reference_start
        year_bs_next = str(int(bs_year) + 1)[-2:]

        try:
            return self.reference_format.format(
                serial=serial,
                year_bs=bs_year,
                year_bs_next=year_bs_next,
                month_bs=bs_month,
            )
        except Exception:
            return f"{serial}/{bs_year}/{year_bs_next}"

    def commit_dispatch_no(self, final_value):
        """Print गर्दा staff ले edit गरेको मानलाई counter मा commit गर्छ।"""
        from .renderer import today_bs_approx
        from .models import NumberCounter
        bs_year = today_bs_approx().split("/")[0]

        obj, _ = NumberCounter.objects.get_or_create(
            institution=self.institution,
            counter_type="dispatch",
            bs_year=bs_year,
            defaults={"last_number": 0},
        )
        try:
            n = int(str(final_value).strip())
        except (ValueError, TypeError):
            return
        if n > obj.last_number:
            obj.last_number = n
            obj.save(update_fields=["last_number"])

    def commit_reference_no(self, final_value):
        """Print गर्दा staff ले edit गरेको reference लाई counter मा commit गर्छ।
        Format बाट पहिलो नम्बर निकाल्छ।"""
        from .renderer import today_bs_approx
        from .models import NumberCounter
        bs_year = today_bs_approx().split("/")[0]

        # "062/2082/83" बाट 62 निकाल्ने
        serial = None
        import re
        m = re.match(r"^\s*(\d+)", str(final_value))
        if m:
            serial = int(m.group(1))

        if serial is None:
            return

        obj, _ = NumberCounter.objects.get_or_create(
            institution=self.institution,
            counter_type="reference",
            bs_year=bs_year,
            defaults={"last_number": 0},
        )
        if serial > obj.last_number:
            obj.last_number = serial
            obj.save(update_fields=["last_number"])
    editable_fields = models.TextField(
            blank=True,
            default=(
                "reference_no|पत्र संख्या|\n"
                "dispatch_no|च. नं.|\n"
                "date|मिति|\n"
                "recipient|प्राप्तकर्ता|\n"
                "subject|विषय|\n"
                "body|मुख्य भाग|\n"
                "signature|हस्ताक्षर|क्याम्पस प्रमुख"
            ),
            help_text=(
                "One field per line: key|label|default\n"
                "Keys must match LetterPadPosition field names:\n"
                "reference_no, dispatch_no, date, recipient, "
                "subject, body, signature"
            ),
        )
        

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
            ordering = ["institution", "name"]
    
    def __str__(self):
                svc = f" / {self.service.name}" if self.service else ""
                return f"{self.institution} — {self.name}{svc}"    

    def parsed_editable_fields(self):
            """
            Returns list of dicts:
            [{"key": "reference_no", "label": "पत्र संख्या", "default": ""}]
            """
            fields = []
            for line in (self.editable_fields or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                key = parts[0] if len(parts) > 0 else ""
                label = parts[1] if len(parts) > 1 else key
                default = parts[2] if len(parts) > 2 else ""
                if key:
                    fields.append({
                        "key": key,
                        "label": label,
                        "default": default,
                    })
            return fields        
    


# ─────────────────────────────────────────────
# GeneratedLetter
# ─────────────────────────────────────────────

class GeneratedLetter(models.Model):
    """
    Stores every final PDF produced.
    Can be linked to an Application (generic) or an Enrollment (campus-only).
    """

    template = models.ForeignKey(
        LetterTemplate,
        on_delete=models.PROTECT,
        related_name="generated",
    )

    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_letters",
    )

    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="letters",
    )

    reference_no = models.CharField(max_length=100, blank=True)
    dispatch_no = models.CharField(max_length=100, blank=True)

    pdf_file = models.FileField(upload_to="generated_letters/%Y/%m/")

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    field_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Letter generate गर्दा प्रयोग भएका सबै field values",
    )

    version = models.PositiveIntegerField(
        default=1,
        help_text="पहिलो generate = 1, edit गरेर फेरि = 2, ...",
    )

    original = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="revisions",
        help_text="यो revision हो भने, मूल letter कुन हो",
    )
    class Meta:
        ordering = ["-generated_at"]
    
    def __str__(self):
        return f"{self.reference_no or self.pk} — {self.template.name}"
class NumberCounter(models.Model):
    COUNTER_TYPES = [
        ("dispatch", "च. नं. / Dispatch"),
        ("reference", "पत्र संख्या / Reference"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="number_counters",
    )

    counter_type = models.CharField(max_length=20, choices=COUNTER_TYPES)
    bs_year = models.CharField(max_length=10)          # "2082"
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("institution", "counter_type", "bs_year")
        ordering = ["institution", "counter_type", "-bs_year"]

    def __str__(self):
        return f"{self.institution} — {self.get_counter_type_display()} — {self.bs_year} → {self.last_number}"

    @classmethod
    def next_number(cls, institution, counter_type, bs_year, start=1):
        """
        Returns (display_no, is_new_year)
        Creates the counter for the year if missing.
        """
        obj, created = cls.objects.get_or_create(
            institution=institution,
            counter_type=counter_type,
            bs_year=bs_year,
            defaults={"last_number": start - 1},
        )
        obj.last_number += 1
        obj.save(update_fields=["last_number"])
        return obj.last_number
    