from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from .models import CustomUser
from subscriptions.models import Subscription
from .forms import CustomUserCreationForm
from courses.models import Course, Category  # 
from .forms import ProfileForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

def instructor_public(request, username: str):
    trainer = get_object_or_404(CustomUser, username=username)
    # Vérifier si l'utilisateur est un formateur ou un administrateur
    if getattr(trainer, 'role', None) not in ['trainer', 'admin'] and not trainer.is_superuser:
        # Rediriger vers le profil public si l'utilisateur n'est pas un formateur
        return redirect('users:profile')
    
    # Le reste du code s'exécute pour les formateurs et les administrateurs
    
    # Vérifier si l'utilisateur actuel est abonné à ce formateur
    is_subscribed = False
    if request.user.is_authenticated and request.user != trainer:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user,
            trainer=trainer,
            is_active=True
        ).exists()
    
    # Compter le nombre d'abonnés
    subscribers_count = trainer.subscribers.filter(is_active=True).count()
    
    courses = Course.objects.filter(created_by=trainer).select_related('category').order_by('-created_at')
    teacher_courses = Course.objects.filter(created_by=trainer).order_by('title')
    categories = Category.objects.all().order_by('name')
    
    # Récupérer toutes les vidéos des cours du formateur
    from courses.models import LessonVideo
    videos = []
    for course in courses:
        course_videos = LessonVideo.objects.filter(
            lesson__module__course=course
        ).select_related('lesson__module').order_by('lesson__module__order', 'lesson__order', 'order')
        
        for video in course_videos:
            videos.append({
                'id': video.id,
                'title': video.title or video.lesson.title,
                'description': video.lesson.description or '',
                'thumbnail_url': video.lesson.thumbnail.url if video.lesson.thumbnail else (
                    course.thumbnail.url if course.thumbnail else None
                ),
                'course_title': course.title,
                'course_id': course.id,
                'duration': video.duration,
                'created_at': getattr(video.lesson, 'created_at', timezone.now()),
                'lesson_id': video.lesson.id
            })
    
    upcoming_sessions = []
    try:
        from classrooms.models import LiveSession
        upcoming_sessions = list(
            LiveSession.objects.filter(classroom__created_by=trainer, start_at__gte=timezone.now())
            .select_related('classroom')
            .order_by('start_at')[:6]
        )
    except Exception:
        upcoming_sessions = []
    
    stats = {
        'courses': courses.count(),
    }
    
    # Vérifier si l'utilisateur vient d'une recherche
    from_search = request.GET.get('from_search') == 'true'
    
    # Récupérer le nombre de messages non lus si l'utilisateur est connecté
    unread_count = 0
    if request.user.is_authenticated and request.user == trainer:
        try:
            from interactions.models import Message
            unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
        except Exception:
            pass
    
    return render(request, 'users/instructor_public.html', {
        'trainer': trainer,
        'courses': courses,
        'teacher_courses': teacher_courses,
        'upcoming_sessions': upcoming_sessions,
        'stats': stats,
        'categories': categories,
        'is_subscribed': is_subscribed,
        'subscribers_count': subscribers_count,
        'from_search': from_search,
        'unread_count': unread_count,
        'videos': videos,
    })

@login_required
def learner_public(request, username: str):
    learner = get_object_or_404(CustomUser, username=username)
    # Ensure the handle matches the logged-in learner
    if request.user.id != learner.id and not request.user.is_superuser:
        return redirect('users:dashboard')
    user = learner
    categories = Category.objects.all()
    category_slug = request.GET.get('category')
    if category_slug:
        courses = Course.objects.filter(category__slug=category_slug)
    else:
        courses = Course.objects.all()
    context = {
        'user': user,
        'courses': courses,
        'categories': categories,
        'selected_category': category_slug,
    }
    return render(request, 'users/dashboard.html', context)

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Vérifier s'il y a une URL de redirection valide
            if next_url and next_url != 'None' and not next_url.startswith('/admin/'):
                return redirect(next_url)
                
            # Redirection selon le rôle
            if user.is_staff or user.is_superuser or getattr(user, 'role', None) == 'admin':
                return redirect('users:admin_dashboard')
            elif getattr(user, 'role', None) == 'trainer':
                return redirect('users:handle_profile', username=user.username)
            elif getattr(user, 'role', None) == 'learner':
                return redirect('users:learner_dashboard_handle', username=user.username)
            else:
                return redirect('users:dashboard')
        else:
            messages.error(request, "Identifiants invalides.")
    
    # Afficher le formulaire de connexion
    next_url = request.GET.get('next', '')
    return render(request, 'users/login.html', {'next': next_url})

@login_required
def user_logout(request):
    logout(request)
    return redirect('users:login')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.save()
                messages.success(request, "Compte créé avec succès, connectez-vous.")
                return redirect('users:login')
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la création du compte: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})

# @login_required
# def dashboard(request):
    user = request.user

    # Récupérer toutes les catégories pour les filtres
    categories = Category.objects.all()

    # Récupérer le slug de catégorie depuis la query string (ex: ?category=python)
    category_slug = request.GET.get('category')

    # Récupérer tous les cours ou filtrer par catégorie si spécifiée
    if category_slug:
        courses = Course.objects.filter(category__slug=category_slug)
    else:
        courses = Course.objects.all()

    context = {
        'user': user,
        'courses': courses,
        'categories': categories,
        'selected_category': category_slug,
    }

    # Logique spécifique selon le rôle (facultative ici)
    if user.role == 'trainer':
        context['trainer_view'] = True
    elif user.role == 'learner':
        context['learner_view'] = True
    elif user.is_superuser or user.role == 'admin':
        context['admin_view'] = True

    return render(request, 'users/dashboard.html', context)

@login_required
def dashboard(request):
    user = request.user
    categories = Category.objects.all()
    category_slug = request.GET.get('category')

    # Récupérer les cours en fonction de la catégorie sélectionnée
    if category_slug:
        courses = Course.objects.filter(category__slug=category_slug)
    else:
        courses = Course.objects.all()

    # Récupérer les leçons terminées par l'utilisateur
    from courses.models import LessonProgress
    completed_lessons = []
    if user.is_authenticated:
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            is_completed=True
        ).values_list('lesson_id', flat=True)

    context = {
        'user': user,
        'courses': courses,
        'categories': categories,
        'selected_category': category_slug,
        'completed_lessons': list(completed_lessons),  # Convertir en liste pour le template
    }

    # Logique spécifique selon le rôle
    if user.role == 'trainer':
        context['trainer_view'] = True
    elif user.role == 'learner':
        context['learner_view'] = True
    elif user.is_superuser or user.role == 'admin':
        context['admin_view'] = True

    return render(request, 'users/dashboard.html', context)
    
@login_required
def instructor_dashboard(request):
    return redirect('handle_profile', username=request.user.username)

@login_required
def learner_dashboard(request):
    context = {'user': request.user, 'message': "Bienvenue sur votre dashboard apprenant !"}
    return render(request, 'users/learner_dashboard.html', context)

@login_required
def learner_dashboard_handle(request, username: str):
    learner = get_object_or_404(CustomUser, username=username)
    if request.user.id != learner.id and not request.user.is_superuser:
        return redirect('users:dashboard')
    # Reuse dashboard content logic
    categories = Category.objects.all()
    category_slug = request.GET.get('category')
    if category_slug:
        courses = Course.objects.filter(category__slug=category_slug)
    else:
        courses = Course.objects.all()
    context = {
        'user': learner,
        'courses': courses,
        'categories': categories,
        'selected_category': category_slug,
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def my_profile(request):
    user = request.user
    # Courses created (if trainer)
    created_courses = Course.objects.filter(created_by=user)
    # Enrollments and courses liked/rated
    try:
        from courses.models import Enrollment, CourseLike, CourseRating
        enrollments = Enrollment.objects.filter(user=user).select_related('course')
        likes = CourseLike.objects.filter(user=user).select_related('course')
        ratings = CourseRating.objects.filter(user=user).select_related('course')
    except Exception:
        enrollments, likes, ratings = [], [], []
    # Classrooms memberships
    try:
        from classrooms.models import ClassroomMembership
        classroom_memberships = ClassroomMembership.objects.filter(user=user).select_related('classroom')
    except Exception:
        classroom_memberships = []
    # Certifications
    try:
        from certifications.models import Certification
        certifications = Certification.objects.filter(user=user)
    except Exception:
        certifications = []
    
    # Nombre de messages non lus
    try:
        from interactions.models import Message
        unread_count = Message.objects.filter(recipient=user, is_read=False).count()
    except Exception:
        unread_count = 0

    context = {
        'me': user,
        'created_courses': created_courses,
        'enrollments': enrollments,
        'likes': likes,
        'ratings': ratings,
        'classroom_memberships': classroom_memberships,
        'certifications': certifications,
        'unread_count': unread_count,
        'is_own_profile': True,
    }
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect('users:profile')
    else:
        form = ProfileForm(instance=user)
    return render(request, 'users/profile_edit.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Mot de passe modifié.")
            return redirect('users:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/password_change.html', {'form': form})

@login_required
def upload_avatar(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        try:
            request.user.avatar = request.FILES['avatar']
            request.user.save(update_fields=['avatar'])
            return JsonResponse({
                'success': True,
                'message': 'Photo de profil mise à jour avec succès.',
                'avatar_url': request.user.avatar.url if request.user.avatar else None
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors du téléchargement de la photo de profil: {str(e)}'
            }, status=400)
    return JsonResponse({
        'success': False,
        'message': 'Aucun fichier fourni.'
    }, status=400)

@login_required
def upload_cover(request):
    if request.method == 'POST' and request.FILES.get('cover'):
        try:
            request.user.cover = request.FILES['cover']
            request.user.save(update_fields=['cover'])
            return JsonResponse({
                'success': True,
                'message': 'Image de couverture mise à jour avec succès.',
                'cover_url': request.user.cover.url if request.user.cover else None
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors du téléchargement de l\'image de couverture: {str(e)}'
            }, status=400)
    return JsonResponse({
        'success': False,
        'message': 'Aucun fichier fourni.'
    }, status=400)

def search_trainers(request):
    """
    Vue pour rechercher des formateurs par nom d'utilisateur ou nom complet
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'trainers': []})
    
    # Recherche des formateurs correspondant à la requête
    trainers = CustomUser.objects.filter(
        Q(role='trainer') | Q(is_superuser=True),
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).distinct()
    
    # Préparation des données des formateurs
    results = []
    current_user = request.user if request.user.is_authenticated else None
    
    for trainer in trainers:
        # Vérifier si l'utilisateur actuel est abonné à ce formateur
        is_subscribed = False
        if current_user and current_user.is_authenticated and current_user != trainer:
            is_subscribed = Subscription.objects.filter(
                subscriber=current_user,
                trainer=trainer,
                is_active=True
            ).exists()
        
        # Compter le nombre d'abonnés et de cours
        subscribers_count = trainer.subscribers.filter(is_active=True).count()
        courses_count = Course.objects.filter(created_by=trainer).count()
        
        results.append({
            'id': trainer.id,
            'username': trainer.username,
            'full_name': trainer.get_full_name(),
            'avatar': trainer.avatar.url if trainer.avatar else None,
            'is_subscribed': is_subscribed,
            'subscribers_count': subscribers_count,
            'courses_count': courses_count
        })
    
    return JsonResponse({'trainers': results})

# Les vues de gestion des abonnements ont été déplacées vers l'application 'subscriptions'
