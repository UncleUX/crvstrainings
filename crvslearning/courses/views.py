from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView
 
from .models import Course, Module, Lesson, UserLessonProgress, Enrollment, LessonProgress, Comment, CourseRating, CourseLike, LessonVideo, Category, CourseCompletion
from evaluations.models import EvaluationLevel
from exercices.models import UserExerciseAttempt
from certifications.models import Certification
from .forms import CourseForm, ModuleForm, LessonForm
from django.utils import timezone
try:
    from classrooms.models import LiveSession
except Exception:
    LiveSession = None

class LessonDetailView(DetailView):
    model = Lesson
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_attempts = {}
        if self.request.user.is_authenticated:
            from exercices.models import UserExerciseAttempt
            attempts = UserExerciseAttempt.objects.filter(
                user=self.request.user,
                exercise__in=self.object.exercises.all()
            ).select_related('selected_choice', 'exercise')
            
            for attempt in attempts:
                user_attempts[attempt.exercise.id] = {
                    'choice_id': attempt.selected_choice.id,
                    'is_correct': attempt.is_correct
                }
        
        context['user_exercise_attempts'] = user_attempts
        return context

def is_formateur(user):
    return (
        user.is_authenticated and (
            getattr(user, 'role', None) == 'trainer' or getattr(user, 'role', None) == 'admin' or user.is_superuser
        )
    )


@user_passes_test(is_formateur)
@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'courses/course_list.html', {'courses': courses})


from django.db.models import Count, Q
from .models import UserLessonProgress, LessonProgress, CourseCompletion

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_enrolled = False
    is_course_completed = False
    progress_percent = 0
    completed_count = 0
    total_lessons = 0
    completed_lesson_ids = set()
    
    if request.user.is_authenticated:
        # Vérifier si l'utilisateur est inscrit
        is_enrolled = Enrollment.objects.filter(
            user=request.user, 
            course=course
        ).exists()
        
        # Vérifier si le cours est marqué comme terminé
        if is_enrolled:
            is_course_completed = False
            try:
                is_course_completed = CourseCompletion.objects.filter(
                    user=request.user,
                    course=course
                ).exists()
            except Exception as e:
                print(f"Erreur lors de la vérification de la complétion du cours: {e}")
            
            # Récupérer tous les IDs de leçons du cours
            lesson_ids = list(Lesson.objects.filter(
                module__course=course
            ).values_list('id', flat=True))
            
            total_lessons = len(lesson_ids)
            completed_count = 0
            completed_lesson_ids = set()
            
            # Récupérer les leçons terminées
            if total_lessons > 0:
                try:
                    completed_lessons = LessonProgress.objects.filter(
                        user=request.user,
                        lesson_id__in=lesson_ids,
                        is_completed=True
                    )
                    completed_count = completed_lessons.count()
                    completed_lesson_ids = set(completed_lessons.values_list('lesson_id', flat=True))
                except Exception as e:
                    print(f"Erreur lors de la récupération des leçons terminées: {e}")
                    completed_count = 0
                    completed_lesson_ids = set()
                progress_percent = int((completed_count / total_lessons) * 100)
                
                # Si toutes les leçons sont terminées, marquer le cours comme terminé
                if not is_course_completed and completed_count == total_lessons:
                    CourseCompletion.objects.get_or_create(
                        user=request.user,
                        course=course
                    )
                    is_course_completed = True
    
    # Obtenir le nombre d'inscrits
    nombre_inscrits = course.enrollments.count()
    modules = course.modules.prefetch_related('lessons', 'lessons__videos').all()

    # Progression par niveau (beginner/intermediate/advanced)
    level_labels = {
        'beginner': 'Débutant',
        'intermediate': 'Intermédiaire',
        'advanced': 'Avancé',
    }
    levels_progress = []
    if is_enrolled:
        for level_key, level_name in level_labels.items():
            level_modules = [m for m in modules if m.level == level_key]
            lesson_ids_level = []
            for m in level_modules:
                lesson_ids_level.extend(list(m.lessons.values_list('id', flat=True)))
            total_level = len(lesson_ids_level)
            done_level = 0
            if total_level:
                from .models import LessonProgress
                done_level = LessonProgress.objects.filter(
                    user=request.user, lesson_id__in=lesson_ids_level, is_completed=True
                ).count()
            percent_level = int((done_level / total_level) * 100) if total_level else 0
            is_level_completed = total_level > 0 and done_level == total_level

            # Evaluation et certification
            evaluation = EvaluationLevel.objects.filter(course=course, level=level_key, is_active=True).first()
            cert = Certification.objects.filter(user=request.user, course=course, level=level_key, is_valid=True).first()

            levels_progress.append({
                'key': level_key,
                'label': level_name,
                'total': total_level,
                'done': done_level,
                'percent': percent_level,
                'completed': is_level_completed,
                'evaluation': evaluation,
                'cert': cert,
            })

    context = {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'completed_count': completed_count,
        'completed_lesson_ids': completed_lesson_ids,
        'progress_percent': progress_percent,
        'total_lessons': total_lessons,
        'completed_count': completed_count,
        'levels_progress': levels_progress,
        'is_course_completed': is_course_completed,
        'completed_lesson_ids': completed_lesson_ids,
    }

    # Course rating & like context
    from django.db.models import Avg
    avg_rating = CourseRating.objects.filter(course=course).aggregate(Avg('rating'))['rating__avg']
    if avg_rating is not None:
        avg_rating = round(avg_rating, 1)
    like_count = CourseLike.objects.filter(course=course).count()
    user_rating_value = None
    user_liked = False
    if request.user.is_authenticated:
        ur = CourseRating.objects.filter(course=course, user=request.user).first()
        if ur:
            user_rating_value = ur.rating
        user_liked = CourseLike.objects.filter(course=course, user=request.user).exists()

    context.update({
        'avg_rating': avg_rating,
        'like_count': like_count,
        'user_rating_value': user_rating_value,
        'user_liked': user_liked,
    })

    return render(request, 'courses/course_detail.html', context)



@login_required
def module_detail(request, course_id, module_id):
    module = get_object_or_404(Module, id=module_id, course__id=course_id)
    lessons = module.lessons.order_by('order')
    return render(request, 'courses/module_detail.html', {'module': module, 'lessons': lessons})


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    first_module = course.modules.order_by('id').first()
    first_lesson = first_module.lessons.order_by('id').first() if first_module else None

    if not is_enrolled and lesson != first_lesson:
        messages.warning(request, "Veuillez vous inscrire pour accéder à cette leçon.")
        return redirect('courses:course_detail', course_id=course.id)
    # Build context for the page
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'is_completed': False}
    )

    # Compte des inscrits
    enrollment_count = Enrollment.objects.filter(course=course).count()

    # Leçon suivante / précédente et playlist suivante
    next_lesson_qs = Lesson.objects.filter(module=lesson.module, order__gt=lesson.order).order_by('order')
    next_lesson = next_lesson_qs.first()
    previous_lesson = Lesson.objects.filter(module=lesson.module, order__lt=lesson.order).order_by('-order').first()
    next_lessons = list(next_lesson_qs)

    # Videos: active video for current lesson and media for next lessons
    lesson_videos = list(lesson.videos.all())
    active_video_url = None
    if lesson_videos:
        active_video_url = lesson_videos[0].video_file.url if lesson_videos[0].video_file else None
    if not active_video_url and getattr(lesson, 'video_file', None):
        # fallback to legacy field
        try:
            active_video_url = lesson.video_file.url
        except Exception:
            active_video_url = None
    # Build playlist entries with media_url to avoid dict subscripting in template
    next_playlist = []
    for nl in next_lessons:
        media_url = None
        first_vid = nl.videos.first()
        if first_vid and first_vid.video_file:
            try:
                media_url = first_vid.video_file.url
            except Exception:
                media_url = None
        if not media_url and getattr(nl, 'video_file', None):
            try:
                media_url = nl.video_file.url
            except Exception:
                media_url = None
        next_playlist.append({'lesson': nl, 'media_url': media_url})

    # Completed lessons for this course (for 'lu' markers)
    completed_ids = set(LessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=course,
        is_completed=True
    ).values_list('lesson_id', flat=True))

    # Level completion and evaluation for CTA
    level_key = getattr(lesson.module, 'level', None)
    level_completed = False
    level_evaluation = None
    if is_enrolled and level_key:
        level_lessons_qs = Lesson.objects.filter(module__course=course, module__level=level_key)
        total_level_lessons = level_lessons_qs.count()
        done_in_level = LessonProgress.objects.filter(user=request.user, lesson__in=level_lessons_qs, is_completed=True).count()
        level_completed = total_level_lessons > 0 and done_in_level == total_level_lessons
        from evaluations.models import EvaluationLevel
        level_evaluation = EvaluationLevel.objects.filter(course=course, level=level_key, is_active=True).first()

    # Combined hierarchical playlist: all current lesson videos then all next lessons videos
    combined_playlist = []
    # current lesson videos
    for idx, lv in enumerate(lesson_videos):
        try:
            url = lv.video_file.url
        except Exception:
            url = None
        if url:
            combined_playlist.append({
                'lesson_id': lesson.id,
                'title': lv.title or f"{lesson.title} - Partie {idx+1}",
                'media_url': url,
                'href': reverse('courses:lesson_detail', args=[lesson.id]),
                'thumbnail_url': lesson.thumbnail.url if lesson.thumbnail else None,
            })
    # fallback if no LessonVideo
    if not combined_playlist and getattr(lesson, 'video_file', None):
        try:
            combined_playlist.append({
                'lesson_id': lesson.id, 
                'title': lesson.title, 
                'media_url': lesson.video_file.url, 
                'href': reverse('courses:lesson_detail', args=[lesson.id]),
                'thumbnail_url': lesson.thumbnail.url if lesson.thumbnail else None,
            })
        except Exception:
            pass
    # next lessons videos
    for nl in next_lessons:
        vids = list(nl.videos.all())
        if vids:
            for j, v in enumerate(vids):
                try:
                    url = v.video_file.url
                except Exception:
                    url = None
                if url:
                    combined_playlist.append({
                        'lesson_id': nl.id,
                        'title': v.title or f"{nl.title} - Partie {j+1}",
                        'media_url': url,
                        'href': reverse('courses:lesson_detail', args=[nl.id]),
                        'thumbnail_url': nl.thumbnail.url if nl.thumbnail else None,
                    })
        elif getattr(nl, 'video_file', None):
            try:
                combined_playlist.append({
                    'lesson_id': nl.id, 
                    'title': nl.title, 
                    'media_url': nl.video_file.url, 
                    'href': reverse('courses:lesson_detail', args=[nl.id]),
                    'thumbnail_url': nl.thumbnail.url if nl.thumbnail else None,
                })
            except Exception:
                pass

    # Get user exercise attempts
    user_exercise_attempts = {}
    if request.user.is_authenticated:
        from exercices.models import UserExerciseAttempt
        attempts = UserExerciseAttempt.objects.filter(
            user=request.user,
            exercise__in=lesson.exercises.all()
        ).select_related('selected_choice', 'exercise')
        
        for attempt in attempts:
            user_exercise_attempts[attempt.exercise.id] = {
                'choice_id': attempt.selected_choice.id,
                'is_correct': attempt.is_correct
            }

    # Comments and ratings context
    comments = list(Comment.objects.filter(lesson=lesson).select_related('user').order_by('-created_at')[:50])
    print(f"Commentaires chargés pour la leçon {lesson.id}: {len(comments)}")
    for c in comments:
        print(f"Commentaire {c.id}: {c.content[:50]}... (par {c.user.username}, {c.created_at})")
    from django.db.models import Avg
    avg_rating = CourseRating.objects.filter(course=course).aggregate(Avg('rating'))['rating__avg']
    if avg_rating is not None:
        avg_rating = round(avg_rating, 1)
    user_rating_value = None
    like_count = CourseLike.objects.filter(course=course).count()
    user_liked = False
    if request.user.is_authenticated:
        ur = CourseRating.objects.filter(course=course, user=request.user).first()
        if ur:
            user_rating_value = ur.rating
        user_liked = CourseLike.objects.filter(course=course, user=request.user).exists()

    # Vérifier si la leçon est marquée comme terminée
    lesson_completed = progress.is_completed if hasattr(progress, 'is_completed') else False
    
    return render(request, 'courses/lesson_detail.html', {
        'lesson': lesson,
        'module': lesson.module,
        'course': course,
        'progress': progress,
        'completed_lesson_ids': list(completed_ids),
        'enrollment_count': enrollment_count,
        'next_lesson': next_lesson,
        'previous_lesson': previous_lesson,
        'next_lessons': next_lessons,
        'next_playlist': next_playlist,
        'is_enrolled': is_enrolled,
        'first_lesson': first_lesson,
        'level_key': level_key,
        'level_completed': level_completed,
        'level_evaluation': level_evaluation,
        'comments': comments,
        'avg_rating': avg_rating,
        'user_rating_value': user_rating_value,
        'like_count': like_count,
        'user_liked': user_liked,
        'lesson_videos': lesson_videos,
        'active_video_url': active_video_url,
        'combined_playlist': combined_playlist,
        'user_exercise_attempts': user_exercise_attempts,
        'lesson_completed': lesson_completed,
    })


@login_required
@require_POST
def add_comment(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course
    # Optional: restrict commenting to enrolled users
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, "Vous devez être inscrit pour commenter.")
        return redirect('courses:lesson_detail', lesson_id=lesson_id)
    content = request.POST.get('content', '').strip()
    if content:
        Comment.objects.create(user=request.user, lesson=lesson, content=content)
        messages.success(request, "Commentaire ajouté.")
    else:
        messages.error(request, "Le commentaire est vide.")
    return redirect('courses:lesson_detail', lesson_id=lesson_id)

@login_required
@require_POST
def rate_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    try:
        rating = int(request.POST.get('rating', '0'))
    except ValueError:
        rating = 0
    if rating < 1 or rating > 5:
        messages.error(request, "Note invalide.")
        return redirect('courses:course_detail', course_id=course.id)
    obj, _ = CourseRating.objects.update_or_create(
        user=request.user, course=course, defaults={'rating': rating}
    )
    messages.success(request, "Votre note a été enregistrée.")
    # Revenir à la leçon si referer indique une leçon
    ref = request.META.get('HTTP_REFERER') or ''
    if '/lessons/' in ref:
        return redirect(ref)
    return redirect('courses:course_detail', course_id=course.id)

@login_required
@require_POST
def toggle_like(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    obj = CourseLike.objects.filter(course=course, user=request.user).first()
    if obj:
        obj.delete()
        messages.info(request, "Vous n'aimez plus ce cours.")
    else:
        CourseLike.objects.create(course=course, user=request.user)
        messages.success(request, "Cours ajouté à vos favoris.")
    ref = request.META.get('HTTP_REFERER') or ''
    if '/lessons/' in ref:
        return redirect(ref)
    return redirect('courses:course_detail', course_id=course.id)



@require_http_methods(["POST"])
@csrf_exempt
def create_category(request):
    if not request.user.is_authenticated or not is_formateur(request.user):
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    
    name = request.POST.get('name')
    if not name:
        return JsonResponse({'success': False, 'error': 'Le nom de la catégorie est requis'}, status=400)
    
    try:
        category = Category.objects.create(name=name)
        return JsonResponse({
            'success': True,
            'category_id': category.id,
            'category_name': category.name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@user_passes_test(is_formateur)
@login_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            
            # Handle category selection
            category_id = request.POST.get('category')
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    course.category = category
                except Category.DoesNotExist:
                    pass
                    
            course.save()
            
            # Handle AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Cours créé avec succès.',
                    'redirect_url': reverse('courses:course_detail', kwargs={'course_id': course.id})
                })
                
            messages.success(request, "Cours créé avec succès.")
            return redirect('courses:course_detail', course_id=course.id)
        else:
            # Handle AJAX request with form errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'form_errors': form.errors,
                    'message': 'Veuillez corriger les erreurs ci-dessous.'
                }, status=400)
                
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = CourseForm(initial={
            'language': 'fr'  # Set default language
        })
    
    # Get all categories for the template
    categories = Category.objects.all().order_by('name')
    
    # Check if this is an AJAX request for initial form load
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'form_html': render_to_string('courses/partials/course_form.html', {
                'form': form,
                'categories': categories
            }, request=request)
        })
        
    return render(request, 'courses/course_form.html', {
        'form': form,
        'categories': categories
    })


@user_passes_test(is_formateur)
@login_required
def module_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, "Module ajouté.")
            return redirect('courses:course_detail', course_id=course.id)
    else:
        form = ModuleForm()
    return render(request, 'courses/module_form.html', {'form': form, 'course': course})


@user_passes_test(is_formateur)
@login_required
def lesson_create(request, course_id, module_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Si module_id est 0, on redirige vers la sélection d'un module
    if int(module_id) == 0:
        modules = Module.objects.filter(course_id=course_id)
        if modules.exists():
            return render(request, 'courses/select_module.html', {
                'course': course,
                'modules': modules
            })
        else:
            # S'il n'y a pas encore de modules, on crée un module par défaut
            module = Module.objects.create(
                course=course,
                title=f"Module 1 - {course.title}",
                description=f"Module par défaut pour {course.title}",
                order=1,
                level='beginner'
            )
            messages.info(request, "Un module par défaut a été créé pour ce cours.")
            return redirect('courses:lesson_create', course_id=course_id, module_id=module.id)
    
    # Si on a un module_id valide
    module = get_object_or_404(Module, id=module_id, course=course)
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                lesson = form.save(commit=False)
                lesson.module = module
                # Si l'ordre n'est pas spécifié, on le définit automatiquement
                if not lesson.order:
                    last_lesson = Lesson.objects.filter(module=module).order_by('-order').first()
                    lesson.order = last_lesson.order + 1 if last_lesson else 1
                lesson.save()
                messages.success(request, "Leçon ajoutée avec succès.")
                return redirect('courses:module_detail', course_id=course_id, module_id=module_id)
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la création de la leçon : {str(e)}")
    else:
        # Pré-remplir le formulaire avec l'ordre suivant
        last_lesson = Lesson.objects.filter(module=module).order_by('-order').first()
        initial = {'order': (last_lesson.order + 1) if last_lesson else 1}
        form = LessonForm(initial=initial)
        
    return render(request, 'courses/lesson_form.html', {
        'form': form, 
        'module': module,
        'course': course,
        'title': 'Ajouter une leçon'
    })


@user_passes_test(is_formateur)
@login_required
def lesson_video_create(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        try:
            order = int(request.POST.get('order') or '1')
        except ValueError:
            order = 1
        video_file = request.FILES.get('video_file')
        if not video_file:
            messages.error(request, "Veuillez sélectionner un fichier vidéo.")
        else:
            LessonVideo.objects.create(lesson=lesson, title=title, video_file=video_file, order=order)
            messages.success(request, "Vidéo ajoutée à la leçon.")
            return redirect('courses:lesson_detail', lesson_id=lesson.id)
    return render(request, 'courses/lesson_video_form.html', {'lesson': lesson})


@login_required
@require_POST
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Only learners can enroll
    if not request.user.is_authenticated or getattr(request.user, 'role', None) != 'learner':
        messages.error(request, "Seuls les apprenants peuvent s'inscrire à un cours.")
        return redirect('courses:course_detail', course_id=course.id)
    enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)
    if created:
        messages.success(request, f"Vous êtes bien inscrit au cours {course.title}.")
    else:
        messages.info(request, f"Vous êtes déjà inscrit à ce cours.")
    return redirect('courses:course_detail', course_id=course.id)

def all_courses(request):
    from .models import Category
    category_slug = request.GET.get('category') or ''
    categories = list(Category.objects.all())

    qs = Course.objects.select_related('category').all()
    selected_category = None
    if category_slug:
        selected_category = next((c for c in categories if c.slug == category_slug), None)
        if selected_category:
            qs = qs.filter(category=selected_category)

    # text search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    highlight_courses = list(Course.objects.order_by('-created_at')[:4])

    upcoming_sessions = []
    if LiveSession is not None:
        try:
            upcoming_sessions = list(
                LiveSession.objects.filter(start_at__gte=timezone.now())
                .select_related('classroom', 'classroom__course')
                .order_by('start_at')[:5]
            )
        except Exception:
            upcoming_sessions = []

    context = {
        'courses': qs,
        'categories': categories,
        'selected_category': selected_category,
        'q': q,
        'highlight_courses': highlight_courses,
        'upcoming_sessions': upcoming_sessions,
    }
    return render(request, 'courses/all_course.html', context)

def search(request):
    q = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')  # 'all', 'channels', 'videos'
    
    course_results = []
    video_results = []
    instructor_results = []
    
    if q:
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Q, Prefetch, Case, When, Value, IntegerField, F
        from django.db.models.functions import Concat, Lower
        User = get_user_model()
        
        # Recherche de formateurs (chaînes)
        if search_type in ['all', 'channels']:
            instructor_results = User.objects.filter(
                Q(username__icontains=q) | 
                Q(first_name__icontains=q) | 
                Q(last_name__icontains=q) |
                Q(bio__icontains=q) |
                Q(email__icontains=q),
                is_active=True,
                role='trainer'
            ).annotate(
                full_name=Concat('first_name', Value(' '), 'last_name'),
                courses_count=Count('courses', distinct=True),
                subscribers_count=Count('subscribers', filter=Q(subscriptions__is_active=True), distinct=True),
                # Score de pertinence
                relevance=Case(
                    When(username__iexact=q, then=Value(100)),
                    When(username__istartswith=q, then=Value(80)),
                    When(full_name__iexact=q, then=Value(70)),
                    When(full_name__icontains=q, then=Value(50)),
                    When(bio__icontains=q, then=Value(30)),
                    default=Value(10),
                    output_field=IntegerField()
                )
            ).order_by('-relevance', '-subscribers_count')
        
        # Recherche de cours
        if search_type in ['all', 'courses']:
            # Construction de la requête de base
            base_query = Course.objects.filter(
                Q(title__icontains=q) | 
                Q(description__icontains=q) |
                Q(category__name__icontains=q) |
                Q(created_by__username__icontains=q) |
                Q(created_by__first_name__icontains=q) |
                Q(created_by__last_name__icontains=q)
            )
            
            # Optimisation des requêtes avec select_related et prefetch_related
            base_query = base_query.select_related('category', 'created_by')
            
            # Préchargement des modules et leçons associés
            base_query = base_query.prefetch_related(
                Prefetch(
                    'modules',
                    queryset=Module.objects.prefetch_related('lessons')
                )
            )
            
            # Ajout des annotations pour le comptage et le score de pertinence
            from django.db.models import Count, Case, When, Value, IntegerField
            
            course_results = base_query.annotate(
                lessons_count=Count('modules__lessons', distinct=True),
                relevance=Case(
                    When(title__iexact=q, then=Value(100)),
                    When(title__istartswith=q, then=Value(80)),
                    When(title__icontains=q, then=Value(60)),
                    When(description__icontains=q, then=Value(30)),
                    default=Value(10),
                    output_field=IntegerField()
                )
            ).order_by('-relevance', '-created_at')[:12]
            
        # Recherche de vidéos
        if search_type in ['all', 'videos']:
            from datetime import datetime
            
            video_results = LessonVideo.objects.filter(
                Q(title__icontains=q) | 
                Q(lesson__title__icontains=q) |
                Q(lesson__module__course__title__icontains=q) |
                Q(lesson__module__course__created_by__username__icontains=q) |
                Q(lesson__module__course__created_by__first_name__icontains=q) |
                Q(lesson__module__course__created_by__last_name__icontains=q)
            ).select_related(
                'lesson', 
                'lesson__module', 
                'lesson__module__course', 
                'lesson__module__course__created_by',
                'lesson__module__course__category'
            ).annotate(
                course_title=F('lesson__module__course__title'),
                instructor_name=Concat(
                    'lesson__module__course__created_by__first_name',
                    Value(' '),
                    'lesson__module__course__created_by__last_name'
                ),
                # Score de pertinence
                relevance=Case(
                    When(title__iexact=q, then=Value(100)),
                    When(title__istartswith=q, then=Value(80)),
                    When(title__icontains=q, then=Value(60)),
                    When(lesson__title__iexact=q, then=Value(70)),
                    When(lesson__title__icontains=q, then=Value(50)),
                    When(lesson__module__course__title__iexact=q, then=Value(60)),
                    When(lesson__module__course__title__icontains=q, then=Value(40)),
                    When(lesson__module__course__created_by__username__iexact=q, then=Value(50)),
                    When(lesson__module__course__created_by__username__icontains=q, then=Value(30)),
                    default=Value(10),
                    output_field=IntegerField()
                )
            ).order_by('-relevance', '-id')
            
            # Si la recherche est spécifiquement pour un formateur, filtrer par son nom d'utilisateur
            if q.startswith('@'):
                username = q[1:].strip()
                video_results = video_results.filter(
                    lesson__module__course__created_by__username__iexact=username
                )
        
        # Si la recherche est spécifiquement pour un formateur et qu'on a un seul résultat exact
        if search_type == 'instructor' and len(instructor_results) == 1:
            exact_match = any([
                q.lower() == instructor_results[0].username.lower(),
                q.lower() == instructor_results[0].get_full_name().lower(),
                q.lower() == instructor_results[0].email.lower()
            ])
            if exact_match:
                return redirect('users:instructor_public', username=instructor_results[0].username)
    
    # Préparer les résultats pour le template
    context = {
        'q': q,
        'search_type': search_type,
        'video_results': video_results[:12] if search_type in ['all', 'videos'] else [],
        'instructor_results': instructor_results[:12] if search_type in ['all', 'channels'] else [],
        'has_results': bool(instructor_results.exists() if hasattr(instructor_results, 'exists') else instructor_results) or 
                      bool(video_results.exists() if hasattr(video_results, 'exists') else video_results),
    }
    
    # Si on est en recherche de formateurs et qu'il n'y a pas de résultats, proposer des suggestions
    if search_type == 'instructor' and not instructor_results and not instructor_channels:
        # Suggérer des formateurs populaires
        from django.db.models import Count
        suggested_instructors = User.objects.filter(
            is_active=True,
            role='trainer'
        ).annotate(
            courses_count=Count('course', distinct=True),
            subscribers_count=Count('subscribers', filter=Q(subscriptions__is_active=True), distinct=True)
        ).order_by('-subscribers_count', '-courses_count')[:5]
        
        if suggested_instructors.exists():
            context['suggested_instructors'] = suggested_instructors
    
    return render(request, 'courses/search.html', context)


def search_suggest(request):
    q = request.GET.get('q', '').strip()
    search_type = request.GET.get('search_type', 'course')
    
    if not q:
        return JsonResponse({'items': []})
        
    items = []
    
    if search_type == 'instructor':
        # Suggestions pour les formateurs
        from django.contrib.auth import get_user_model
        User = get_user_model()
        instructors = User.objects.filter(
            Q(username__icontains=q) | 
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) |
            Q(bio__icontains=q) |
            Q(email__icontains=q),
            is_active=True,
            role='instructor'  # Utilisation du champ role au lieu de is_instructor
        ).distinct()[:5]
        
        for instructor in instructors:
            full_name = f"{instructor.first_name} {instructor.last_name}".strip()
            if not full_name:
                full_name = instructor.username
            items.append({
                'type': 'instructor', 
                'id': instructor.id, 
                'label': f"Formateur: {full_name}", 
                'url': reverse('handle_profile', args=[instructor.username])
            })
    else:
        # Suggestions pour les cours
        courses = Course.objects.filter(
            Q(title__icontains=q) |
            Q(created_by__username__icontains=q) |
            Q(created_by__first_name__icontains=q) |
            Q(created_by__last_name__icontains=q)
        ).select_related('created_by').distinct().order_by('title')[:5]
        
        for course in courses:
            items.append({
                'type': 'course', 
                'id': course.id, 
                'label': f"{course.title} (par {course.created_by.get_full_name() or course.created_by.username})", 
                'url': reverse('courses:course_detail', args=[course.id])
            })
            
        # Ajouter aussi les leçons si nécessaire
        lessons = Lesson.objects.filter(
            Q(title__icontains=q) | 
            Q(description__icontains=q)
        ).select_related('module', 'module__course').distinct().order_by('title')[:3]
        
        for lesson in lessons:
            items.append({
                'type': 'lesson', 
                'id': lesson.id, 
                'label': f"Leçon: {lesson.title} - {lesson.module.course.title}", 
                'url': reverse('courses:lesson_detail', args=[lesson.id])
            })
    
    return JsonResponse({'items': items})


# -------- Trainer helper APIs (JSON) --------
@login_required
@user_passes_test(is_formateur)
def api_my_courses(request):
    qs = Course.objects.filter(created_by=request.user).order_by('title').values('id', 'title')
    return JsonResponse({'courses': list(qs)})


@login_required
@user_passes_test(is_formateur)
def api_modules_for_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, created_by=request.user)
    qs = course.modules.order_by('id').values('id', 'title')
    return JsonResponse({'modules': list(qs)})


@login_required
@user_passes_test(is_formateur)
def api_lessons_for_module(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__created_by=request.user)
    qs = module.lessons.order_by('order', 'id').values('id', 'title')
    return JsonResponse({'lessons': list(qs)})

@login_required
def module_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled:
        messages.error(request, "Vous devez être inscrit pour accéder aux modules.")
        return redirect('courses:course_detail', course_id=course.id)

    modules = course.modules.all()
    return render(request, 'courses/module_list.html', {
        'course': course,
        'modules': modules,
    })


@require_http_methods(["POST"])
@login_required
def mark_lesson_completed(request, lesson_id):
    from django.db import transaction
    from django.utils import timezone
    from django.http import JsonResponse
    
    try:
        with transaction.atomic():
            # Récupérer la leçon avec ses relations
            lesson = Lesson.objects.select_related(
                'module', 
                'module__course'
            ).prefetch_related(
                'module__lessons'
            ).get(id=lesson_id)
            
            course = lesson.module.course
            module = lesson.module
            
            # Vérifier que l'utilisateur est inscrit au cours
            if not Enrollment.objects.filter(
                user=request.user, 
                course=course
            ).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Vous devez être inscrit à ce cours pour marquer des leçons comme terminées.'
                }, status=403)
            
            # Vérifier si la leçon est déjà marquée comme terminée
            progress, created = LessonProgress.objects.get_or_create(
                user=request.user,
                lesson=lesson,
                defaults={'is_completed': True, 'completed_at': timezone.now()}
            )
            
            # Basculer l'état de complétion
            was_completed = progress.is_completed
            progress.is_completed = not was_completed
            progress.completed_at = timezone.now() if progress.is_completed else None
            progress.save()
            
            # Mettre à jour les statistiques de progression
            total_lessons = Lesson.objects.filter(module__course=course).count()
            completed_lessons = LessonProgress.objects.filter(
                user=request.user,
                lesson__module__course=course,
                is_completed=True
            ).count()
            
            # Vérifier si le module est maintenant terminé
            module_lessons = module.lessons.all()
            module_lesson_ids = list(module_lessons.values_list('id', flat=True))
            completed_module_lessons = LessonProgress.objects.filter(
                user=request.user,
                lesson_id__in=module_lesson_ids,
                is_completed=True
            ).count()
            
            module_completed = (completed_module_lessons == len(module_lessons))
            
            # Vérifier si le cours est maintenant terminé
            course_completed = (completed_lessons == total_lessons)
            if course_completed and progress.is_completed:  # Seulement si on marque comme terminé
                CourseCompletion.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={'completed_at': timezone.now()}
                )
            elif not progress.is_completed and course_completed:
                # Si on décoche une leçon et que le cours était marqué comme terminé
                CourseCompletion.objects.filter(
                    user=request.user,
                    course=course
                ).delete()
            
            # Préparer la réponse
            response_data = {
                'status': 'success',
                'completed': progress.is_completed,
                'lesson_id': lesson.id,
                'module_id': module.id,
                'course_id': course.id,
                'progress': {
                    'completed': completed_lessons,
                    'total': total_lessons,
                    'percent': int((completed_lessons / total_lessons * 100)) if total_lessons > 0 else 0
                },
                'module': {
                    'completed': module_completed,
                    'completed_lessons': completed_module_lessons,
                    'total_lessons': len(module_lessons)
                },
                'course_completed': course_completed,
                'message': f'Leçon marquée comme {"terminée" if progress.is_completed else "non terminée"} avec succès.'
            }
            
            return JsonResponse(response_data)
            
    except Lesson.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Leçon non trouvée.'
        }, status=404)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'Une erreur est survenue: {str(e)}'
        }, status=500)


@login_required
@require_POST
def mark_module_completed(request, course_id, module_id):
    module = get_object_or_404(Module, id=module_id, course__id=course_id)

    if not Enrollment.objects.filter(user=request.user, course=module.course).exists():
        messages.error(request, "Vous devez être inscrit pour marquer ce module terminé.")
        return redirect('courses:course_detail', course_id=course_id)

    from .models import LessonProgress
    lesson_ids = list(module.lessons.values_list('id', flat=True))
    for lid in lesson_ids:
        lp, _ = LessonProgress.objects.get_or_create(user=request.user, lesson_id=lid)
        if not lp.is_completed:
            lp.is_completed = True
            lp.save(update_fields=['is_completed'])

    messages.success(request, "Module marqué comme terminé.")
    return redirect('courses:course_detail', course_id=course_id)

@require_http_methods(["POST"])
@login_required
def mark_course_completed(request, course_id):
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    from .models import CourseCompletion, LessonProgress
    from django.db import transaction
    
    try:
        course = Course.objects.get(id=course_id)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Vérifier que l'utilisateur est inscrit au cours
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Vous devez être inscrit pour marquer ce cours comme terminé.'
                }, status=403)
            messages.error(request, "Vous devez être inscrit pour marquer ce cours comme terminé.")
            return redirect('courses:course_detail', course_id=course_id)
        
        with transaction.atomic():
            # Vérifier si le cours est déjà marqué comme terminé
            completion, created = CourseCompletion.objects.get_or_create(
                user=request.user,
                course=course
            )
            
            if not created:
                # Si le cours était déjà marqué comme terminé, on le marque comme non terminé
                completion.delete()
                is_completed = False
                message = "Le cours n'est plus marqué comme terminé."
                progress_percent = 0
            else:
                # Marquer toutes les leçons du cours comme terminées
                lessons = Lesson.objects.filter(module__course=course)
                total_lessons = lessons.count()
                
                for lesson in lessons:
                    LessonProgress.objects.update_or_create(
                        user=request.user,
                        lesson=lesson,
                        defaults={'is_completed': True}
                    )
                
                is_completed = True
                message = "Le cours a été marqué comme terminé avec succès."
                progress_percent = 100
        
        # Préparer la réponse
        response_data = {
            'status': 'success',
            'completed': is_completed,
            'message': message,
            'progress': {
                'completed': total_lessons if is_completed else 0,
                'total': total_lessons,
                'percent': progress_percent
            }
        }
        
        if is_ajax:
            return JsonResponse(response_data)
            
        messages.success(request, message)
        return redirect('courses:course_detail', course_id=course_id)
        
    except Course.DoesNotExist:
        error_message = 'Cours non trouvé.'
        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=404)
        messages.error(request, error_message)
        return redirect('courses:all_courses')
        
    except Exception as e:
        error_message = f'Une erreur est survenue: {str(e)}'
        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=500)
        messages.error(request, error_message)
        return redirect('courses:course_detail', course_id=course_id)

# ... (le reste du code reste inchangé)
