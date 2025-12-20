from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from courses.models import Course, LessonProgress, LearningPath, Enrollment

User = get_user_model()

@login_required
def learner_dashboard(request):
    """Tableau de bord de l'apprenant avec statistiques de progression"""
    user = request.user
    
    # Récupérer le parcours d'apprentissage
    learning_path, created = LearningPath.objects.get_or_create(user=user)
    
    # Récupérer les cours de l'apprenant
    enrolled_courses = user.enrollments.select_related('course').order_by('-enrolled_at')
    
    # Statistiques générales
    stats = {
        'total_courses': enrolled_courses.count(),
        'completed_courses': learning_path.completed_courses.count(),
        'in_progress_courses': enrolled_courses.exclude(course__in=learning_path.completed_courses.all()).count(),
        'total_lessons_completed': LessonProgress.objects.filter(user=user, is_completed=True).count(),
    }
    
    # Progression des cours
    courses_progress = []
    for enrollment in enrolled_courses:
        course = enrollment.course
        total_lessons = course.modules.aggregate(total=Count('lessons'))['total'] or 0
        completed_lessons = LessonProgress.objects.filter(
            user=user, 
            lesson__module__course=course, 
            is_completed=True
        ).count()
        
        progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        
        courses_progress.append({
            'course': course,
            'progress': round(progress, 1),
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'last_activity': learning_path.last_activity if learning_path.current_course == course else None
        })
    
    # Dernières activités
    recent_activities = LessonProgress.objects.filter(
        user=user,
        is_completed=True
    ).select_related('lesson', 'lesson__module', 'lesson__module__course').order_by('-completed_at')[:5]
    
    context = {
        'learning_path': learning_path,
        'stats': stats,
        'courses_progress': courses_progress,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'users/learner_dashboard.html', context)

@login_required
def course_progress(request, course_id):
    """Détail de la progression pour un cours spécifique"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    # Vérifier que l'utilisateur est inscrit au cours
    if not user.enrollments.filter(course=course).exists():
        return redirect('course_detail', course_id=course_id)
    
    # Récupérer les modules et leçons avec la progression
    modules = []
    total_lessons = 0
    completed_lessons = 0
    
    for module in course.modules.all().prefetch_related('lessons'):
        module_lessons = []
        for lesson in module.lessons.all():
            progress = LessonProgress.objects.filter(
                user=user,
                lesson=lesson
            ).first()
            
            module_lessons.append({
                'lesson': lesson,
                'is_completed': progress.is_completed if progress else False,
                'completed_at': progress.completed_at if progress else None
            })
            
            if progress and progress.is_completed:
                completed_lessons += 1
            total_lessons += 1
        
        modules.append({
            'module': module,
            'lessons': module_lessons,
            'progress': (len([l for l in module_lessons if l['is_completed']]) / len(module_lessons) * 100) if module_lessons else 0
        })
    
    course_progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    context = {
        'course': course,
        'modules': modules,
        'course_progress': round(course_progress, 1),
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
    }
    
    return render(request, 'users/course_progress.html', context)


@require_http_methods(["POST"])
def update_learning_time(request):
    """Met à jour le temps passé sur la plateforme"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Non authentifié'}, status=401)
    
    try:
        time_spent_seconds = int(request.POST.get('time_spent', 60))
        learning_path = LearningPath.objects.get(user=request.user)
        learning_path.time_spent += timezone.timedelta(seconds=time_spent_seconds)
        learning_path.save()
        return JsonResponse({'status': 'success'})
    except (ValueError, LearningPath.DoesNotExist) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
