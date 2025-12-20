from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.conf import settings

from .models import EvaluationLevel, Attempt, EvaluationQuestion, EvaluationChoice, AttemptAnswer
from courses.models import Course, Lesson
from certifications.models import Certification

import os
import qrcode
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors


def _user_level_completion(user, course, level: str) -> dict:
    modules = course.modules.filter(level=level).prefetch_related('lessons')
    lesson_ids = []
    for m in modules:
        lesson_ids.extend(list(m.lessons.values_list('id', flat=True)))

    total = len(lesson_ids)
    if total == 0:
        return {"total": 0, "done": 0, "percent": 0, "completed": False}

    from courses.models import LessonProgress
    done = LessonProgress.objects.filter(user=user, lesson_id__in=lesson_ids, is_completed=True).count()
    percent = int((done / total) * 100)
    return {"total": total, "done": done, "percent": percent, "completed": done == total}


def _generate_certificate_pdf(cert: Certification, score: float) -> str:
    # Prepare paths
    media_root = getattr(settings, 'MEDIA_ROOT', '.')
    out_dir = os.path.join(media_root, 'certificates')
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{cert.code}.pdf")

    # Create QR/verify URL
    verify_host = settings.ALLOWED_HOSTS[0] if getattr(settings, 'ALLOWED_HOSTS', []) else 'localhost'
    scheme = 'https'
    if settings.DEBUG:
        scheme = 'http'
    base_url = f"{scheme}://{verify_host}"
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    if not media_url.endswith('/'):
        media_url += '/'
    qr_target = f"{base_url}{media_url}certificates/{cert.code}.pdf"
    qr_img = qrcode.make(qr_target)
    qr_path = os.path.join(out_dir, f"{cert.code}.png")
    qr_img.save(qr_path)

    # Try to load a logo from static if present
    logo_path = None
    candidate_paths = []
    static_root = getattr(settings, 'STATIC_ROOT', '')
    if static_root:
        candidate_paths.append(os.path.join(static_root, 'img', 'logo.png'))
    for p in getattr(settings, 'STATICFILES_DIRS', []):
        candidate_paths.append(os.path.join(p, 'img', 'logo.png'))
    for p in candidate_paths:
        if os.path.exists(p):
            logo_path = p
            break

    # Build PDF in landscape A4
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    width, height = landscape(A4)
    c.setTitle("Certification")

    # Background: subtle geometric lines
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(0.5)
    margin = 36
    # diagonal mesh
    for x in range(0, int(width) + 200, 120):
        c.line(x - 200, margin, x, height - margin)
    for x in range(0, int(width) + 200, 120):
        c.line(x - 200, height - margin, x, margin)

    # Header: logo top-left
    if logo_path:
        try:
            c.drawImage(ImageReader(logo_path), margin, height - 90, width=140, height=40, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    else:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, height - 70, "CRVS TRAININGS")

    # Title block centered
    center_x = width / 2
    y = height - 140
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(center_x, y, "Civil Status Registration Office (BUNEC) certifies that")

    # Recipient name
    y -= 34
    recipient = (cert.user.get_full_name() or cert.user.username).upper()
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(center_x, y, recipient)

    # Lead-in line
    y -= 28
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, y, "has successfully completed all program requirements and is certified as a")

    # Certificate title (red)
    y -= 36
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor('#dc2626'))  # red-600
    title_text = f"CRVS {cert.course.title} EXPERT"
    c.drawCentredString(center_x, y, title_text)

    # Subtitles (level + module)
    c.setFillColor(colors.black)
    y -= 24
    level_label = str(cert.get_level_display() if hasattr(cert, 'get_level_display') else cert.level)
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, y, f"Level: {level_label}")

    # Optional: module label (take first module matching level)
    try:
        mod = cert.course.modules.filter(level=cert.level).first()
        if mod:
            y -= 18
            c.drawCentredString(center_x, y, f"Module: {mod.title}")
    except Exception:
        pass

    # Signature area bottom-left
    sig_y = 90
    c.setFont("Helvetica", 11)
    c.drawString(margin, sig_y + 28, "Alexandre M. YOMO")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(margin, sig_y + 14, "General Manager, BUNEC")
    # signature line
    c.setLineWidth(1)
    c.line(margin, sig_y + 8, margin + 220, sig_y + 8)

    # Seal bottom-right in grey box
    seal_w, seal_h = 70, 80
    seal_x, seal_y = width - margin - seal_w, 60
    c.setFillColor(colors.HexColor('#f3f4f6'))
    c.roundRect(seal_x, seal_y, seal_w, seal_h, 10, fill=True, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(seal_x + seal_w/2, seal_y + seal_h/2 + 6, "")
    try:
        c.drawImage(ImageReader(qr_path), seal_x + seal_w - 64, seal_y + 6, width=65, height=65, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    # Footer meta: date and certificate number
    from django.utils import timezone
    issue_date = timezone.now().strftime('%B %d, %Y')
    c.setFont("Helvetica", 10)
    footer_text = f"Date of Issue: {issue_date} — Certificate Number: {cert.code}"
    c.drawCentredString(center_x, 36, footer_text)

    c.showPage()
    c.save()
    return pdf_path


@login_required
def start_evaluation(request: HttpRequest, course_id: int, level: str) -> HttpResponse:
    course = get_object_or_404(Course, id=course_id)
    evaluation = get_object_or_404(EvaluationLevel, course=course, level=level, is_active=True)

    # Gate: ensure level is completed
    comp = _user_level_completion(request.user, course, level)
    if not comp["completed"]:
        messages.error(request, "Veuillez compléter toutes les leçons de ce niveau avant l'évaluation.")
        return redirect('courses:course_detail', course_id=course.id)

    # Enforce attempts rule: max 3 attempts total unless a success occurred earlier
    attempts_qs = Attempt.objects.filter(user=request.user, evaluation=evaluation)
    already_passed = attempts_qs.filter(passed=True).exists()
    attempts_count = attempts_qs.count()
    if already_passed:
        messages.error(request, "Vous avez déjà réussi cette évaluation. Nouvelle tentative non autorisée.")
        return redirect('courses:course_detail', course_id=course.id)
    if attempts_count >= 3:
        messages.error(request, "Nombre maximum de 3 tentatives atteint pour cette évaluation.")
        return redirect('courses:course_detail', course_id=course.id)

    if request.method == 'POST':
        # QCM grading
        questions = list(EvaluationQuestion.objects.filter(evaluation=evaluation).prefetch_related('choices'))
        total_points = sum(q.points for q in questions) or 1
        earned_points = 0

        attempt = Attempt.objects.create(user=request.user, evaluation=evaluation, score=0.0, passed=False)

        for q in questions:
            choice_id = request.POST.get(f'q_{q.id}')
            chosen = None
            if choice_id:
                try:
                    chosen = EvaluationChoice.objects.get(id=int(choice_id), question=q)
                except (EvaluationChoice.DoesNotExist, ValueError):
                    chosen = None
            AttemptAnswer.objects.create(attempt=attempt, question=q, choice=chosen)
            if chosen and chosen.is_correct:
                earned_points += q.points

        percent = round((earned_points / total_points) * 100, 2)
        passed = percent >= evaluation.threshold
        attempt.score = percent
        attempt.passed = passed
        attempt.save(update_fields=['score', 'passed'])

        if passed:
            # Create or get Certification
            cert, created = Certification.objects.get_or_create(
                user=request.user, course=course, level=level
            )
            # Generate PDF if not set
            if not cert.pdf:
                pdf_path = _generate_certificate_pdf(cert, percent)
                media_root = getattr(settings, 'MEDIA_ROOT', '')
                try:
                    rel_path = os.path.relpath(str(pdf_path), str(media_root))
                except Exception:
                    rel_path = str(pdf_path)
                rel_path = rel_path.lstrip(os.sep)
                cert.pdf.name = rel_path
                cert.save()

            messages.success(request, f"Félicitations ! Vous avez réussi avec {percent}%.")
            return redirect('courses:course_detail', course_id=course.id)
        else:
            messages.error(request, f"Échec à l'évaluation ({percent}%). Vous pouvez réessayer.")
            return redirect('evaluations:start_level_evaluation', course_id=course.id, level=level)

    # GET: render QCM
    questions = EvaluationQuestion.objects.filter(evaluation=evaluation).prefetch_related('choices')
    return render(request, 'evaluations/start_evaluation.html', {
        'course': course,
        'evaluation': evaluation,
        'level': level,
        'threshold': evaluation.threshold,
        'questions': questions,
    })
