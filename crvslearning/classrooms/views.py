from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Classroom, ClassroomMembership, LiveSession
from courses.models import Category
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import os

# ======================================================
# UTILITAIRE : vérifier si l'utilisateur est enseignant
# ======================================================
def is_teacher(user):
    return user.is_authenticated and (getattr(user, 'role', None) in ['trainer', 'admin'] or user.is_superuser)

# ======================================================
# MES CLASSES
# ======================================================
@login_required
def my_classrooms(request):
    memberships = ClassroomMembership.objects.filter(user=request.user).select_related('classroom')
    categories = Category.objects.all().order_by('name')
    return render(request, 'classrooms/my_classrooms.html', {'memberships': memberships, 'categories': categories})

# ======================================================
# CRÉATION DE CLASSE (ENSEIGNANT)
# ======================================================
@user_passes_test(is_teacher)
@login_required
def classroom_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category_id')
        schedule = request.POST.get('schedule', '').strip()
        category = None
        if category_id:
            category = get_object_or_404(Category, id=category_id)
        else:
            messages.error(request, "Veuillez sélectionner une catégorie pour cette classe.")
            return redirect('classrooms:create')
        if not name:
            messages.error(request, "Le nom est requis.")
            return redirect('classrooms:create')
        classroom = Classroom.objects.create(
            name=name,
            subject=subject,
            description=description,
            category=category,
            created_by=request.user,
            schedule=schedule,
        )
        ClassroomMembership.objects.create(classroom=classroom, user=request.user, role='teacher')
        messages.success(request, f"Classe créée. Code d'invitation: {classroom.join_code}")
        return redirect('classrooms:detail', classroom_id=classroom.id)

    # Minimal course list for selection
    categories = Category.objects.all().order_by('name')
    return render(request, 'classrooms/create.html', {'categories': categories})


# ======================================================
# DÉTAIL D'UNE CLASSE
# ======================================================
@login_required
def classroom_detail(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    is_member = ClassroomMembership.objects.filter(classroom=classroom, user=request.user).exists()
    is_teacher_member = ClassroomMembership.objects.filter(classroom=classroom, user=request.user, role='teacher').exists() or classroom.created_by_id == request.user.id
    if not is_member and not is_teacher_member:
        messages.error(request, "Accès réservé aux membres de cette classe. Rejoignez via un code.")
        return redirect('classrooms:join')
    return render(request, 'classrooms/detail.html', {'classroom': classroom, 'is_member': is_member, 'is_teacher_member': is_teacher_member})


# ======================================================
# PLANIFIER UNE SESSION LIVE
# ======================================================
@user_passes_test(is_teacher)
@login_required
def session_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        classroom_id = request.POST.get('classroom_id')
        start_at = request.POST.get('start_at')  # ISO datetime local
        description = request.POST.get('description', '').strip()
        if not title or not classroom_id or not start_at:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('classrooms:session_create')
        classroom = get_object_or_404(Classroom, id=classroom_id)
        # verify teacher ownership/membership
        if classroom.created_by_id != request.user.id and not ClassroomMembership.objects.filter(classroom=classroom, user=request.user, role='teacher').exists():
            messages.error(request, "Vous n'avez pas les droits pour planifier dans cette classe.")
            return redirect('classrooms:session_create')
        try:
            # parse as naive local, let DB/timezone handle
            dt = timezone.make_aware(timezone.datetime.fromisoformat(start_at)) if 'T' in start_at else timezone.make_aware(timezone.datetime.fromisoformat(start_at + ':00'))
        except Exception:
            messages.error(request, "Format de date invalide.")
            return redirect('classrooms:session_create')
        LiveSession.objects.create(classroom=classroom, title=title, start_at=dt, description=description)
        messages.success(request, "Session planifiée.")
        return redirect('classrooms:detail', classroom_id=classroom.id)
    # show only classrooms where user is teacher
    my_classes = Classroom.objects.filter(created_by=request.user) | Classroom.objects.filter(memberships__user=request.user, memberships__role='teacher')
    my_classes = my_classes.distinct()
    return render(request, 'classrooms/session_create.html', {'classrooms': my_classes})

# ======================================================
# WEBHOOK ENREGISTREMENT (JIBRI)
# ======================================================
# Webhook pour enregistrement Jibri/Jitsi (Option A)
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def recording_webhook(request):
    """Réception de l'URL d'enregistrement d'une session live.
    Attendu: JSON { "session_id": <int>, "recording_url": <str> }
    """
    # Optional secret header validation
    expected = os.getenv('WEBHOOK_TOKEN')
    if expected:
      token = request.headers.get('X-Webhook-Token') or request.META.get('HTTP_X_WEBHOOK_TOKEN')
      if not token or token != expected:
          return HttpResponseBadRequest('invalid token')
    try:
        import json
        payload = json.loads(request.body.decode('utf-8'))
        session_id = int(payload.get('session_id'))
        recording_url = payload.get('recording_url')
    except Exception:
        return HttpResponseBadRequest('invalid payload')
    if not session_id or not recording_url:
        return HttpResponseBadRequest('missing fields')
    session = get_object_or_404(LiveSession, id=session_id)
    session.recording_url = recording_url
    session.recording_ready = True
    session.save(update_fields=['recording_url', 'recording_ready'])
    return JsonResponse({'status': 'ok'})

# ======================================================
# DÉMARRER UNE SESSION LIVE (ENSEIGNANT)
# ======================================================
@login_required
def session_start(request, session_id: int):
    from .models import LiveSession
    session = get_object_or_404(LiveSession, id=session_id)
    classroom = session.classroom
    # Only class creator or teacher-members can start
    is_teacher = classroom.created_by_id == request.user.id or ClassroomMembership.objects.filter(classroom=classroom, user=request.user, role='teacher').exists()
    if not is_teacher:
        messages.error(request, "Vous n'avez pas les droits pour démarrer cette session.")
        return redirect('classrooms:detail', classroom_id=classroom.id)
    # Deterministic Jitsi room name using classroom join_code and session id
    room_slug = f"CRVS_{classroom.join_code}_{session.id}"
    # Pass display name for convenience
    display = urlsafe_base64_encode(force_bytes(request.user.get_full_name() or request.user.username))
    base = os.getenv('MEETING_BASE_URL', 'https://meet.jit.si').rstrip('/')
    url = f"{base}/{room_slug}#userInfo.displayName={display}"
    return redirect(url)


# ======================================================
# REJOINDRE UNE SESSION LIVE (MEMBRES)
# ======================================================
@login_required
def session_join(request, session_id: int):
    from .models import LiveSession
    session = get_object_or_404(LiveSession, id=session_id)
    classroom = session.classroom
    # Must be member (student or teacher) to join
    is_member = ClassroomMembership.objects.filter(classroom=classroom, user=request.user).exists() or classroom.created_by_id == request.user.id
    if not is_member:
        messages.error(request, "Accès réservé aux membres de cette classe.")
        return redirect('classrooms:join')
    room_slug = f"CRVS_{classroom.join_code}_{session.id}"
    display = urlsafe_base64_encode(force_bytes(request.user.get_full_name() or request.user.username))
    base = os.getenv('MEETING_BASE_URL', 'https://meet.jit.si').rstrip('/')
    url = f"{base}/{room_slug}#userInfo.displayName={display}"
    return redirect(url)


# ======================================================
# REJOINDRE UNE CLASSE PAR CODE
# ======================================================
@login_required
def join_by_code(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        classroom = Classroom.objects.filter(join_code=code).first()
        if not classroom:
            messages.error(request, "Code invalide.")
            return redirect('classrooms:join')
        # Prevent teachers from joining as student if they are creator
        role = 'student'
        if classroom.created_by_id == request.user.id:
            role = 'teacher'
        obj, created = ClassroomMembership.objects.get_or_create(classroom=classroom, user=request.user, defaults={'role': role})
        if created:
            messages.success(request, f"Vous avez rejoint la classe '{classroom.name}'.")
        else:
            messages.info(request, f"Vous êtes déjà membre de cette classe.")
        return redirect('classrooms:detail', classroom_id=classroom.id)
    return render(request, 'classrooms/join.html')
