from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import models
import json

from .models import (
    LetterPad, LetterPadPosition,
    LetterTemplate, GeneratedLetter,
    NumberCounter,
)
from .pdf_utils import generate_letter_pdf
from .renderer import build_field_values
from applications.models import Application, ApplicationAction


# ─────────────────────────────────────────────
# Letter Pad Editor
# ─────────────────────────────────────────────

@staff_member_required
def letterpad_editor(request, pk):
    letter_pad = get_object_or_404(LetterPad, pk=pk)

    if letter_pad.pdf_file and not letter_pad.preview_image:
        try:
            letter_pad.generate_preview_image()
        except Exception as e:
            return render(request, "letters/letterpad_editor.html", {
                "letter_pad": letter_pad,
                "error": f"Could not generate preview: {e}",
            })

    positions = {
        p.field_name: {
            "x": p.x, "y": p.y,
            "width": p.width, "height": p.height,
            "font_size": p.font_size,
            "alignment": p.alignment,
        }
        for p in letter_pad.positions.all()
    }

    context = {
        "letter_pad": letter_pad,
        "field_choices": LetterPadPosition.FIELD_CHOICES,
        "positions_json": json.dumps(positions),
        "page_width": letter_pad.page_width,
        "page_height": letter_pad.page_height,
    }
    return render(request, "letters/letterpad_editor.html", context)


@staff_member_required
@csrf_exempt
def save_positions(request, pk):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    letter_pad = get_object_or_404(LetterPad, pk=pk)
    data = json.loads(request.body.decode("utf-8"))

    for field_name, pos in data.items():
        LetterPadPosition.objects.update_or_create(
            letter_pad=letter_pad,
            field_name=field_name,
            defaults={
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "width": pos.get("width", 200),
                "height": pos.get("height", 20),
                "font_size": pos.get("font_size", 12),
                "alignment": pos.get("alignment", "left"),
            },
        )

    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────
# Preview Final PDF (sample data)
# ─────────────────────────────────────────────

SAMPLE_VALUES = {
    "reference_no": "०६२/२०८२/८३",
    "dispatch_no": "१०८४",
    "date": "२०८२/११/२५",
    "recipient": "श्री श्याम बहादुर थापा\nसुखड, कैलाली",
    "subject": "छात्रवृत्ति सम्बन्धी सिफारिस ।",
    "body": (
        "उपर्युक्त सम्बन्धमा यस क्याम्पसमा अध्ययनरत छात्र श्री श्याम बहादुर थापाको "
        "छात्रवृत्तिको लागि सिफारिस गर्न अनुरोध गर्दछु। उनको सम्पूर्ण शैक्षिक "
        "विवरण र चरित्र प्रमाणपत्र यसै सिफारिससँग संलग्न रहेको छ।"
    ),
    "signature": "क्याम्पस प्रमुख",
}


@staff_member_required
def preview_final_pdf(request, pk):
    letter_pad = get_object_or_404(LetterPad, pk=pk)

    if not letter_pad.pdf_file:
        return HttpResponse("No PDF uploaded for this letter pad.", status=400)

    try:
        pdf_bytes = generate_letter_pdf(letter_pad, SAMPLE_VALUES)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return HttpResponse(
            f"<h3>PDF generation failed</h3>"
            f"<pre style='white-space:pre-wrap'>{e}</pre>"
            f"<hr><pre style='white-space:pre-wrap;font-size:12px'>{tb}</pre>",
            status=500,
            content_type="text/html",
        )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="preview_{pk}.pdf"'
    return response


# ─────────────────────────────────────────────
# Generate from Application
# ─────────────────────────────────────────────

@staff_member_required
def generate_for_application(request, application_pk):
    application = get_object_or_404(Application, pk=application_pk)
    service = application.service

    templates = LetterTemplate.objects.filter(
        active=True,
        institution=service.institution,
    ).filter(
        models.Q(service=service) | models.Q(service__isnull=True)
    )

    if request.method == "POST":
        template_id = request.POST.get("template_id")
        template = get_object_or_404(LetterTemplate, pk=template_id)

        field_values = build_field_values(template, application)
        pdf_bytes = generate_letter_pdf(template.letter_pad, field_values)

        gl = GeneratedLetter(
            template=template,
            application=application,
            reference_no=field_values.get("reference_no", ""),
            dispatch_no=field_values.get("dispatch_no", ""),
            generated_by=request.user,
            field_values=field_values,
            version=1,
        )
        filename = f"letter_{application.application_no}_{template.pk}.pdf"
        gl.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        ApplicationAction.objects.create(
            application=application,
            action="note",
            acted_by=request.user,
            remarks=f"Letter generated: {template.name}",
        )

        return redirect(gl.pdf_file.url)

    return render(request, "letters/generate_for_application.html", {
        "application": application,
        "templates": templates,
    })


# ─────────────────────────────────────────────
# CREATE LETTER — daily staff page
# ─────────────────────────────────────────────

@staff_member_required
def create_letter(request):
    """
    Actions:
      load    → reload page with the selected template's fields
      preview → stream a PDF preview (opens in new tab)
      print   → save as GeneratedLetter AND commit counters, then redirect to PDF
    """
    from .renderer import today_bs_approx

    templates = LetterTemplate.objects.filter(active=True).order_by(
        "institution", "name"
    )

    selected_template = None
    editable_fields = []

    template_id = request.POST.get("template_id") or request.GET.get("template_id")
    action = request.POST.get("action", "load")

    if template_id:
        selected_template = get_object_or_404(LetterTemplate, pk=template_id)
        editable_fields = selected_template.parsed_editable_fields()

    # ─── Build the values dict field by field ───
    values = {}
    if selected_template:
        bs = today_bs_approx()
        bs_year = bs.split("/")[0]

        for f in editable_fields:
            key = f["key"]

            # ---------- मिति / date ----------
            if key == "date":
                values[key] = request.POST.get(f"field_{key}", "").strip() or bs

            # ---------- च. नं. / dispatch_no ----------
            elif key == "dispatch_no" and selected_template.auto_dispatch:
                posted = request.POST.get(f"field_{key}", "").strip()

                if action == "load":
                    values[key] = str(selected_template.preview_dispatch_no())
                elif action == "preview":
                    values[key] = posted or str(selected_template.preview_dispatch_no())
                elif action == "print":
                    if posted:
                        values[key] = posted
                        selected_template.commit_dispatch_no(posted)
                    else:
                        n = NumberCounter.next_number(
                            selected_template.institution,
                            "dispatch", bs_year,
                            start=selected_template.dispatch_start,
                        )
                        values[key] = str(n)
                else:
                    values[key] = posted or str(selected_template.preview_dispatch_no())

            # ---------- पत्र संख्या / reference_no ----------
            elif key == "reference_no" and selected_template.auto_reference:
                posted = request.POST.get(f"field_{key}", "").strip()

                if action == "load":
                    values[key] = selected_template.preview_reference_no()
                elif action == "preview":
                    values[key] = posted or selected_template.preview_reference_no()
                elif action == "print":
                    if posted:
                        values[key] = posted
                        selected_template.commit_reference_no(posted)
                    else:
                        values[key] = selected_template.preview_reference_no()
                        NumberCounter.next_number(
                            selected_template.institution,
                            "reference", bs_year,
                            start=selected_template.reference_start,
                        )
                else:
                    values[key] = posted or selected_template.preview_reference_no()

            # ---------- All other fields ----------
            else:
                values[key] = request.POST.get(f"field_{key}", f["default"])

    # ─── Preview: stream the PDF, do NOT save ───
    if selected_template and action == "preview":
        pdf_bytes = generate_letter_pdf(selected_template.letter_pad, values)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="preview.pdf"'
        return response

    # ─── Print: save the PDF + counters, then redirect ───
    if selected_template and action == "print":
        pdf_bytes = generate_letter_pdf(selected_template.letter_pad, values)

        # Version history
        original_id = request.POST.get("original_id")
        original = None
        version = 1
        if original_id:
            original = GeneratedLetter.objects.filter(pk=original_id).first()
            if original:
                version = (original.revisions.count() or 0) + 2

        gl = GeneratedLetter(
            template=selected_template,
            reference_no=values.get("reference_no", ""),
            dispatch_no=values.get("dispatch_no", ""),
            generated_by=request.user,
            field_values=values,
            version=version,
            original=original,
        )
        filename = (
            f"letter_{selected_template.pk}_v{version}_"
            f"{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        )
        gl.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        return redirect(gl.pdf_file.url)

    # ─── Load: put filled values back so form re-renders ───
    if selected_template:
        for f in editable_fields:
            f["default"] = values.get(f["key"], f["default"])

    return render(request, "letters/create_letter.html", {
        "templates": templates,
        "selected_template": selected_template,
        "editable_fields": editable_fields,
        "original_id": request.POST.get("original_id", ""),
    })


# ─────────────────────────────────────────────
# Regenerate an existing letter (version history)
# ─────────────────────────────────────────────

@staff_member_required
def regenerate_letter(request, pk):
    """
    Pre-fill the Create Letter page with an existing letter's values.
    Printing again will create a new version.
    """
    original = get_object_or_404(GeneratedLetter, pk=pk)
    template = original.template

    editable_fields = template.parsed_editable_fields()
    saved = original.field_values or {}

    for f in editable_fields:
        if f["key"] in saved:
            f["default"] = saved[f["key"]]

    templates = LetterTemplate.objects.filter(active=True).order_by("institution", "name")

    return render(request, "letters/create_letter.html", {
        "templates": templates,
        "selected_template": template,
        "editable_fields": editable_fields,
        "original_id": original.pk,
        "original_letter": original,
    })


# ─────────────────────────────────────────────
# CREATE NOTICE — same as create_letter, but filtered templates
# ─────────────────────────────────────────────

@staff_member_required
def create_notice(request):
    from .renderer import today_bs_approx

    templates = LetterTemplate.objects.filter(
        active=True,
    ).filter(
        models.Q(name__icontains="notice") | models.Q(name__icontains="सूचना")
    ).order_by("institution", "name")

    selected_template = None
    editable_fields = []

    template_id = request.POST.get("template_id") or request.GET.get("template_id")
    action = request.POST.get("action", "load")

    if template_id:
        selected_template = get_object_or_404(LetterTemplate, pk=template_id)
        editable_fields = selected_template.parsed_editable_fields()

    values = {}
    if selected_template:
        bs = today_bs_approx()
        for f in editable_fields:
            key = f["key"]
            if key == "date":
                values[key] = request.POST.get(f"field_{key}", "").strip() or bs
            else:
                values[key] = request.POST.get(f"field_{key}", f["default"])

    if selected_template and action == "preview":
        pdf_bytes = generate_letter_pdf(selected_template.letter_pad, values)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="preview.pdf"'
        return response

    if selected_template and action == "print":
        pdf_bytes = generate_letter_pdf(selected_template.letter_pad, values)
        gl = GeneratedLetter(
            template=selected_template,
            reference_no=values.get("reference_no", ""),
            dispatch_no=values.get("dispatch_no", ""),
            generated_by=request.user,
            field_values=values,
            version=1,
        )
        filename = f"notice_{selected_template.pk}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        gl.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        return redirect(gl.pdf_file.url)

    if selected_template:
        for f in editable_fields:
            f["default"] = values.get(f["key"], f["default"])

    return render(request, "letters/create_notice.html", {
        "templates": templates,
        "selected_template": selected_template,
        "editable_fields": editable_fields,
    })