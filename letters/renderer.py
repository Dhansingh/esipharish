from datetime import date
from django.template import Template, Context


def today_bs_approx():
    """
    Rough AD → BS conversion (approximate).
    Replace later with a proper nepali-datetime library.
    """
    ad = date.today()
    bs_year = ad.year + 56
    bs_month = ad.month + 8
    bs_day = ad.day + 15
    if bs_day > 32:
        bs_day -= 30
        bs_month += 1
    if bs_month > 12:
        bs_month -= 12
        bs_year += 1
    return f"{bs_year:04d}/{bs_month:02d}/{bs_day:02d}"


def build_context(application):
    """
    Generic context for any application-driven letter.
    Works for campus, ward, TU, government office — anything.
    """
    field_map = application.field_map()

    return {
        "application": application,
        "service": application.service,
        "institution": application.service.institution,
        "department": application.service.department,
        "field_map": field_map,
        "today_bs": today_bs_approx(),
        "today_ad": date.today().strftime("%Y-%m-%d"),
        # Convenience shortcuts
        "applicant_name": application.applicant_name,
        "applicant_phone": application.applicant_phone,
        "applicant_email": application.applicant_email,
        "applicant_address": application.applicant_address,
        "application_no": application.application_no,
        "status": application.get_status_display(),
    }


def render_field(template_str, ctx):
    if not template_str:
        return ""
    return Template(template_str).render(Context(ctx)).strip()


def build_field_values(template, application):
    """
    Returns dict: field_name → rendered string, ready for the PDF engine.
    """
    ctx = build_context(application)

    return {
        "reference_no": render_field(template.reference_no_template, ctx),
        "dispatch_no":  render_field(template.dispatch_no_template, ctx),
        "date":         render_field(template.date_template, ctx),
        "recipient":    render_field(template.recipient_template, ctx),
        "subject":      render_field(template.subject_template, ctx),
        "body":         render_field(template.body_template, ctx),
        "signature":    render_field(template.signature_template, ctx),
    }