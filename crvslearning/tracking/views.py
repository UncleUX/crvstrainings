from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from users.models import CustomUser
from courses.models import Course, Enrollment, Lesson, Module
from .models import UserProgress, LearnerProgress, CourseStatistics, ActivityLog

# Vérifie si l'utilisateur est un formateur ou un administrateur
def is_trainer_or_admin(user):
    return user.is_authenticated and (user.role == 'trainer' or user.is_superuser)

class TrainerOrAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est un formateur ou un administrateur"""
    def test_func(self):
        return is_trainer_or_admin(self.request.user)

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_trainer_or_admin), name='dispatch')
class LearnerTrackingView(TemplateView):
    template_name = 'tracking/learner_tracking.html'
    paginate_by = 10
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer tous les apprenants avec des statistiques
        learners = CustomUser.objects.filter(role='learner').annotate(
            courses_enrolled=Count('enrollments', distinct=True),
            courses_completed=Count('completed_courses', distinct=True),
            lessons_completed=Count('lessonprogress', filter=Q(lessonprogress__is_completed=True), distinct=True),
            last_activity=Coalesce('last_login', 'date_joined')
        ).order_by('-last_activity')
        
        # Calculer les statistiques globales
        total_learners = learners.count()
        active_learners = learners.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Calculer le taux de complétion moyen
        completion_rate = 0
        avg_courses = 0
        
        if total_learners > 0:
            # Calculer le taux de complétion moyen
            completion_rates = []
            for learner in learners:
                total_enrollments = learner.courses_enrolled
                completed = learner.courses_completed
                rate = (completed / total_enrollments * 100) if total_enrollments > 0 else 0
                completion_rates.append(rate)
            
            completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
            
            # Calculer la moyenne des cours par apprenant
            avg_courses = sum(l.courses_enrolled for l in learners) / total_learners
        
        # Pagination
        page = self.request.GET.get('page', 1)
        paginator = Paginator(learners, self.paginate_by)
        
        try:
            learners_page = paginator.page(page)
        except PageNotAnInteger:
            learners_page = paginator.page(1)
        except EmptyPage:
            learners_page = paginator.page(paginator.num_pages)
        
        # Préparer les données pour le template
        learners_data = []
        for learner in learners_page:
            # Calculer les taux de complétion pour cet apprenant
            course_completion_rate = (learner.courses_completed / learner.courses_enrolled * 100) if learner.courses_enrolled > 0 else 0
            
            # Calculer le taux de complétion des leçons
            total_lessons = Lesson.objects.filter(module__course__enrollments__user=learner).count()
            lesson_completion_rate = (learner.lessons_completed / total_lessons * 100) if total_lessons > 0 else 0
            
            # Calculer la différence pour l'affichage
            lesson_only_completion = max(0, lesson_completion_rate - course_completion_rate)
            
            learners_data.append({
                'user': learner,
                'courses_enrolled': learner.courses_enrolled,
                'courses_completed': learner.courses_completed,
                'course_completion_rate': round(course_completion_rate, 1),
                'lesson_completion_rate': round(lesson_completion_rate, 1),
                'lesson_only_completion': round(lesson_only_completion, 1),  # Nouveau champ
                'last_activity': learner.last_login or learner.date_joined
            })
        
        context.update({
            'learners': learners_data,
            'page_obj': learners_page,
            'paginator': paginator,
            'is_paginated': learners_page.has_other_pages(),
            'total_learners': total_learners,
            'active_learners': active_learners,
            'completion_rate': round(completion_rate, 1),
            'avg_courses_per_learner': round(avg_courses, 1),
            'title': 'Suivi des apprenants',
        })
        
        return context

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_trainer_or_admin), name='dispatch')
class CourseProgressView(TemplateView):
    template_name = 'tracking/course_progress.html'
    paginate_by = 10
    
    def get_queryset(self):
        from courses.models import LessonProgress, CourseCompletion
        
        # Récupérer les cours avec des statistiques
        queryset = Course.objects.all()
        
        # Filtrer par créateur si l'utilisateur n'est pas superutilisateur
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        # Récupérer le nombre de leçons complétées par cours
        completed_lessons = (
            LessonProgress.objects
            .filter(is_completed=True)
            .values('lesson__module__course')
            .annotate(completed_count=Count('id', distinct=True))
        )
        
        # Récupérer le nombre de cours complétés par cours
        completed_courses = (
            CourseCompletion.objects
            .values('course')
            .annotate(completed_count=Count('id', distinct=True))
        )
        
        # Créer des dictionnaires pour un accès rapide
        completed_lessons_dict = {item['lesson__module__course']: item['completed_count'] 
                                for item in completed_lessons}
        
        completed_courses_dict = {item['course']: item['completed_count']
                                for item in completed_courses}
        
        # Annoter les cours avec les statistiques
        queryset = queryset.annotate(
            total_enrollments=Count('enrollments', distinct=True),
            total_lessons=Count('modules__lessons', distinct=True),
            average_rating=Coalesce(Avg('ratings__rating'), 0.0),
            last_activity=Max('enrollments__enrolled_at')
        )
        
        # Ajouter les statistiques à chaque cours
        for course in queryset:
            course.completed_lessons_count = completed_lessons_dict.get(course.id, 0)
            course.completed_courses_count = completed_courses_dict.get(course.id, 0)
            
        return queryset.order_by('-last_activity')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les cours avec statistiques
        courses = self.get_queryset()
        
        # Préparer les données pour le graphique
        course_titles = list(courses.values_list('title', flat=True)[:10])
        completion_rates = []
        enrollment_counts = []
        course_completion_rates = []
        
        for course in courses[:10]:  # Limiter à 10 cours pour le graphique
            total_lessons = course.total_lessons or 1  # Éviter la division par zéro
            completed_lessons = getattr(course, 'completed_lessons_count', 0)
            rate = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0
            
            # Calculer le taux de complétion des cours (nombre de cours complétés / nombre d'inscriptions)
            total_enrollments = course.total_enrollments or 1
            completed_courses = getattr(course, 'completed_courses_count', 0)
            course_completion_rate = (completed_courses / total_enrollments) * 100
            
            completion_rates.append(round(rate, 1))
            course_completion_rates.append(round(course_completion_rate, 1))
            enrollment_counts.append(course.total_enrollments)
        
        # Préparer les données pour le tableau
        courses_data = []
        for course in courses:
            total_lessons = course.total_lessons or 1
            completed_lessons = getattr(course, 'completed_lessons_count', 0)
            lesson_completion_rate = (completed_lessons / total_lessons) * 100 if total_lessons > 0 else 0
            
            # Calculer le taux de complétion du cours (nombre de cours complétés / nombre d'inscriptions)
            total_enrollments = course.total_enrollments or 1
            completed_courses = getattr(course, 'completed_courses_count', 0)
            course_completion_rate = (completed_courses / total_enrollments) * 100
            
            # Calculer la différence entre le taux de complétion des leçons et des cours
            lesson_only_completion = max(0, lesson_completion_rate - course_completion_rate)
            
            courses_data.append({
                'id': course.id,
                'title': course.title,
                'instructor': course.created_by,
                'category': course.category,
                'thumbnail': course.thumbnail,
                'is_published': getattr(course, 'is_published', False),
                'enrollments': course.total_enrollments,
                'completed_lessons': completed_lessons,
                'completed_courses': completed_courses,
                'total_lessons': total_lessons,
                'lesson_completion_rate': round(lesson_completion_rate, 1),
                'course_completion_rate': round(course_completion_rate, 1),
                'lesson_only_completion': round(lesson_only_completion, 1),
                'average_rating': round(course.average_rating, 1) if course.average_rating else 0.0,
                'created_at': course.created_at,
                'updated_at': getattr(course, 'updated_at', course.created_at),
            })
        
        # Trier les cours par taux de complétion des cours pour le top 5
        top_courses = sorted(courses_data, key=lambda x: x['course_completion_rate'], reverse=True)[:5]
        
        # Pagination
        page = self.request.GET.get('page', 1)
        paginator = Paginator(courses_data, self.paginate_by)
        
        try:
            courses_page = paginator.page(page)
        except PageNotAnInteger:
            courses_page = paginator.page(1)
        except EmptyPage:
            courses_page = paginator.page(paginator.num_pages)
        
        # Convertir les listes en JSON pour le JavaScript
        import json
        
        context.update({
            'courses': courses_page,
            'top_courses': top_courses,
            'page_obj': courses_page,
            'paginator': paginator,
            'is_paginated': courses_page.has_other_pages(),
            'course_titles': json.dumps([str(title) for title in course_titles]),
            'completion_rates': completion_rates,  # Taux de complétion des leçons
            'course_completion_rates': course_completion_rates,  # Taux de complétion des cours
            'enrollment_counts': enrollment_counts,
            'title': 'Progression des cours',
        })
        
        return context

# Vues basées sur des fonctions pour la rétrocompatibilité
@login_required
@user_passes_test(is_trainer_or_admin)
def learner_tracking(request):
    view = LearnerTrackingView.as_view()
    return view(request)

@login_required
@user_passes_test(is_trainer_or_admin)
def course_progress(request):
    view = CourseProgressView.as_view()
    return view(request)

@login_required
@user_passes_test(is_trainer_or_admin)
def learner_detail(request, learner_id):
    """
    Vue détaillée pour un apprenant spécifique
    """
    learner = get_object_or_404(CustomUser, id=learner_id, role='learner')
    
    # Récupérer les progressions de l'apprenant
    learner_progress = LearnerProgress.objects.filter(user=learner).select_related('course')
    
    # Récupérer les cours complétés via CourseCompletion
    from courses.models import CourseCompletion
    completed_course_ids = set(CourseCompletion.objects.filter(
        user=learner
    ).values_list('course_id', flat=True))
    
    # Créer une liste des inscriptions avec les données de progression
    enrollments = []
    for enrollment in Enrollment.objects.filter(user=learner).select_related('course'):
        progress = learner_progress.filter(course=enrollment.course).first()
        
        # Utiliser CourseCompletion pour déterminer si le cours est complété
        is_course_completed = enrollment.course.id in completed_course_ids
        
        # Mettre à jour l'objet enrollment avec les données de progression
        enrollment.progress = progress.completion_percentage if progress else 0.0
        enrollment.last_accessed = progress.last_accessed if progress else None
        enrollment.completed = is_course_completed
        
        # Si le cours est marqué comme complété mais que la progression est < 100%,
        # forcer la progression à 100%
        if is_course_completed and enrollment.progress < 100:
            enrollment.progress = 100.0
        
        enrollments.append(enrollment)
    
    # Calculer les statistiques
    total_courses = len(enrollments)
    completed_courses = len(completed_course_ids)
    completion_rate = (completed_courses / total_courses * 100) if total_courses > 0 else 0
    
    # Récupérer les activités récentes
    from courses.models import LessonProgress
    recent_activities = LessonProgress.objects.filter(
        user=learner
    ).select_related(
        'lesson', 'lesson__module', 'lesson__module__course'
    ).order_by('-completed_at' if 'completed_at' in [f.name for f in LessonProgress._meta.fields] else '-last_accessed')[:10]
    
    # Calculer le temps total passé sur la plateforme
    total_time_spent = timedelta()
    
    context = {
        'title': f'Détails de {learner.get_full_name() or learner.username}',
        'learner': learner,
        'enrollments': enrollments,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'completion_rate': round(completion_rate, 1),
        'recent_activities': recent_activities,
        'total_time_spent': total_time_spent,
    }
    
    return render(request, 'tracking/learner_detail.html', context)

@login_required
@user_passes_test(is_trainer_or_admin)
def course_detail(request, course_id):
    """Vue détaillée pour un cours spécifique"""
    from courses.models import CourseCompletion, LessonProgress
    
    course = get_object_or_404(Course, id=course_id)
    
    # Vérifier que l'utilisateur a le droit de voir ce cours
    if not request.user.is_superuser and course.instructor != request.user:
        return redirect('tracking:course_progress')
    
    # Récupérer les inscriptions avec progression
    enrollments = Enrollment.objects.filter(course=course).select_related('user')
    
    # Récupérer les utilisateurs ayant complété le cours via CourseCompletion
    completed_user_ids = set(CourseCompletion.objects.filter(
        course=course
    ).values_list('user_id', flat=True))
    
    # Mettre à jour les inscriptions avec l'état de complétion
    for enrollment in enrollments:
        enrollment.completed = enrollment.user_id in completed_user_ids
    
    # Calculer les statistiques du cours
    total_learners = enrollments.count()
    completed_learners = len(completed_user_ids)
    completion_rate = (completed_learners / total_learners * 100) if total_learners > 0 else 0
    
    # Récupérer les modules et leçons avec progression
    modules = course.modules.all().prefetch_related('lessons')
    
    # Récupérer les statistiques de progression des leçons
    lesson_stats = {}
    for module in modules:
        for lesson in module.lessons.all():
            completed_count = LessonProgress.objects.filter(
                lesson=lesson,
                is_completed=True
            ).count()
            
            lesson_stats[lesson.id] = {
                'completed': completed_count,
                'completion_rate': (completed_count / total_learners * 100) if total_learners > 0 else 0
            }
    
    # Préparer les données pour le graphique de progression
    completion_data = []
    for module in modules:
        module_completion = enrollments.filter(progress__lesson__module=module).aggregate(
            avg_completion=Avg('progress__completion')
        )
        completion_data.append({
            'module': module,
            'completion': module_completion['avg_completion'] or 0
        })
    
    context = {
        'course': course,
        'modules': modules,
        'total_learners': total_learners,
        'completed_learners': completed_learners,
        'completion_rate': round(completion_rate, 1),
        'completion_data': completion_data,
        'title': f'Statistiques - {course.title}',
    }
    
    return render(request, 'tracking/course_detail.html', context)
