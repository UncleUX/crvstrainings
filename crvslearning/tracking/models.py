from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, DurationField
from django.db.models.functions import Coalesce
from courses.models import Course, Lesson, Module
from users.models import CustomUser

class LearnerProgress(models.Model):
    """
    Suivi de la progression d'un apprenant dans un cours
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='learner_progress')
    completed_lessons = models.ManyToManyField(Lesson, blank=True, related_name='completed_by')
    completed_modules = models.ManyToManyField(Module, blank=True, related_name='completed_by')
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.FloatField(default=0.0)
    last_accessed = models.DateTimeField(auto_now=True)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Progression Apprenant'
        verbose_name_plural = 'Progression des Apprenants'
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.completion_percentage}%)"

    def update_progress(self):
        """
        Met à jour le pourcentage de complétion du cours
        """
        total_lessons = self.course.get_total_lessons()
        if total_lessons > 0:
            completed = self.completed_lessons.count()
            self.completion_percentage = (completed / total_lessons) * 100
            
            # Mettre à jour la date de complétion si le cours est terminé
            if self.completion_percentage >= 100 and not self.is_completed:
                self.is_completed = True
                self.completion_date = timezone.now()
            elif self.completion_percentage < 100 and self.is_completed:
                self.is_completed = False
                self.completion_date = None
                
            self.save()


class CourseStatistics(models.Model):
    """
    Statistiques agrégées pour un cours
    """
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='statistics')
    total_enrollments = models.PositiveIntegerField(default=0)
    total_completions = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    average_completion_time = models.DurationField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Statistiques du Cours'
        verbose_name_plural = 'Statistiques des Cours'

    def __str__(self):
        return f"Statistiques pour {self.course.title}"

    def update_statistics(self):
        """
        Met à jour les statistiques du cours
        """
        from django.db.models import Avg, F, ExpressionWrapper, DurationField
        from django.db.models.functions import Coalesce
        
        # Compter le nombre total d'inscriptions
        self.total_enrollments = self.course.enrollments.count()
        
        # Compter le nombre de complétions
        self.total_completions = self.course.learner_progress.filter(is_completed=True).count()
        
        # Calculer la note moyenne
        avg_rating = self.course.ratings.aggregate(avg=Avg('rating'))['avg']
        self.average_rating = avg_rating if avg_rating is not None else 0.0
        
        # Calculer le temps moyen de complétion
        completed_progress = self.course.learner_progress.filter(
            is_completed=True,
            completion_date__isnull=False,
            enrollment_date__isnull=False
        )
        
        if completed_progress.exists():
            avg_time = completed_progress.annotate(
                completion_time=ExpressionWrapper(
                    F('completion_date') - F('enrollment_date'),
                    output_field=DurationField()
                )
            ).aggregate(avg=Avg('completion_time'))['avg']
            
            if avg_time:
                self.average_completion_time = avg_time
        
        self.save()


class ActivityLog(models.Model):
    """
    Journal d'activité des utilisateurs
    """
    ACTION_CHOICES = [
        ('view_lesson', 'A consulté une leçon'),
        ('complete_lesson', 'A terminé une leçon'),
        ('start_course', 'A commencé un cours'),
        ('complete_course', 'A terminé un cours'),
        ('enroll', 'S\'est inscrit à un cours'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journaux d'activité"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.timestamp} - {self.get_action_display()}"


class UserProgress(models.Model):
    """
    Suivi de la progression d'un utilisateur dans une leçon spécifique
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    completion_percentage = models.FloatField(default=0.0)
    last_accessed = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.DurationField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Progression de la leçon'
        verbose_name_plural = 'Progressions des leçons'
        unique_together = ('user', 'lesson')
    
    def __str__(self):
        status = "Terminé" if self.completed else f"En cours ({self.completion_percentage}%)"
        return f"{self.user.username} - {self.lesson.title} - {status}"
    
    def save(self, *args, **kwargs):
        # Mettre à jour la date de complétion si la leçon est marquée comme terminée
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
            self.completion_percentage = 100.0
        
        # Mettre à jour la progression du module et du cours
        super().save(*args, **kwargs)
        self.update_module_progress()
    
    def update_module_progress(self):
        """Met à jour la progression du module parent"""
        from .models import LearnerProgress
        
        try:
            # Récupérer ou créer l'entrée de progression pour ce cours
            learner_progress, created = LearnerProgress.objects.get_or_create(
                user=self.user,
                course=self.lesson.module.course,
                defaults={
                    'completion_percentage': 0.0,
                    'is_completed': False
                }
            )
            
            # Mettre à jour les leçons complétées
            if self.completed:
                learner_progress.completed_lessons.add(self.lesson)
                
                # Vérifier si le module est complété
                module_lessons = self.lesson.module.lessons.all()
                completed_lessons = learner_progress.completed_lessons.filter(
                    module=self.lesson.module
                ).count()
                
                if completed_lessons == module_lessons.count():
                    learner_progress.completed_modules.add(self.lesson.module)
            
            # Mettre à jour le pourcentage de complétion global du cours
            total_lessons = self.lesson.module.course.get_total_lessons()
            if total_lessons > 0:
                completed = learner_progress.completed_lessons.filter(
                    module__course=self.lesson.module.course
                ).count()
                learner_progress.completion_percentage = (completed / total_lessons) * 100
                
                # Vérifier si le cours est complété
                if learner_progress.completion_percentage >= 100:
                    learner_progress.is_completed = True
                    learner_progress.completion_date = timezone.now()
                else:
                    learner_progress.is_completed = False
                    learner_progress.completion_date = None
                
                learner_progress.save()
                
                # Mettre à jour les statistiques du cours
                course_stats, created = CourseStatistics.objects.get_or_create(
                    course=self.lesson.module.course
                )
                course_stats.update_statistics()
                
        except Exception as e:
            # Gérer les erreurs potentielles (comme les cours ou modules manquants)
            print(f"Erreur lors de la mise à jour de la progression: {e}")
    
    def get_time_spent_display(self):
        """Retourne le temps passé formaté de manière lisible"""
        if not self.time_spent:
            return "Non suivi"
            
        total_seconds = int(self.time_spent.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}min"
        elif minutes > 0:
            return f"{minutes}min {seconds}s"
        else:
            return f"{seconds}s"
