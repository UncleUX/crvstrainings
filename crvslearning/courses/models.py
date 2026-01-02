from django.db import models
from datetime import timedelta
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    thumbnail = models.ImageField(upload_to='course/thumbnails/', null=True, blank=True)
    language = models.CharField(
        max_length=10,
        choices=[('fr', 'Français'), ('en', 'English')],
        default='fr'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Module(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Débutant'),
        ('intermediate', 'Intermédiaire'),
        ('advanced', 'Avancé'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')  # Niveau ici
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"



class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content_file = models.FileField(upload_to='lessons/files/', blank=True, null=True)
    # video_file = models.FileField(upload_to='lessons/videos/', blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField('Active', default=True)
    thumbnail = models.ImageField(upload_to='lessons/thumbnails/', blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class LessonVideo(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255, blank=True)
    video_file = models.FileField(upload_to='lessons/videos/')
    order = models.PositiveIntegerField(default=1)
    duration = models.DurationField(blank=True, null=True)

    class Meta:
        ordering = ['order', 'id']

    @property
    def views_count(self):
        return self.views.count()

    def __str__(self):
        return self.title or f"Video #{self.pk} for {self.lesson.title}"

class UserLessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'lesson')


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} on {self.lesson}: {self.content[:30]}"


class CourseRating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} → {self.course}: {self.rating}"
       
class CourseLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-created_at']

    def __str__(self):
        return f"❤ {self.user} → {self.course}"

class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.user.username} inscrit à {self.course.title}"
        

class CourseCompletion(models.Model):
    """Modèle pour suivre les cours marqués comme terminés par les utilisateurs"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='completed_courses')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-completed_at']
        verbose_name = 'Achèvement de cours'
        verbose_name_plural = 'Achèvements de cours'
    
    def __str__(self):
        return f"{self.user.username} a terminé {self.course.title}"

class LearningPath(models.Model):
    """Modèle pour suivre le parcours d'apprentissage d'un utilisateur"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='learning_path'
    )
    current_course = models.ForeignKey(
        'Course', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='active_learners'
    )
    current_lesson = models.ForeignKey(
        'Lesson', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='active_learners'
    )
    completed_courses = models.ManyToManyField(
        'Course',
        related_name='completed_by',
        blank=True
    )
    skills_acquired = models.JSONField(
        default=dict,
        help_text="Compétences acquises avec leur niveau"
    )
    learning_goals = models.TextField(
        blank=True,
        null=True,
        help_text="Objectifs d'apprentissage de l'utilisateur"
    )
    last_activity = models.DateTimeField(auto_now=True)
    time_spent = models.DurationField(
        default=timedelta(),
        help_text="Temps total passé sur la plateforme"
    )

    def __str__(self):
        return f"Parcours de {self.user.username}"

    def update_progress(self, lesson, is_completed=True):
        """Met à jour la progression d'une leçon"""
        progress, created = LessonProgress.objects.get_or_create(
            user=self.user,
            lesson=lesson,
            defaults={'is_completed': is_completed}
        )
        
        if not created and is_completed and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save()
        
        # Mettre à jour la leçon en cours
        self.current_lesson = lesson
        self.current_course = lesson.module.course
        self.last_activity = timezone.now()
        self.save()
        
        # Vérifier si le cours est complété
        self._check_course_completion()
        
        return progress

    def _check_course_completion(self):
        """Vérifie si l'utilisateur a terminé tous les modules du cours actuel"""
        if not self.current_course:
            return False
            
        total_lessons = Lesson.objects.filter(
            module__course=self.current_course
        ).count()
        
        completed_lessons = LessonProgress.objects.filter(
            user=self.user,
            lesson__module__course=self.current_course,
            is_completed=True
        ).count()
        
        if total_lessons > 0 and completed_lessons >= total_lessons:
            self.completed_courses.add(self.current_course)
            return True
        return False

    def get_progress_stats(self):
        """Retourne les statistiques de progression"""
        if not self.current_course:
            return {}
            
        total_lessons = Lesson.objects.filter(
            module__course=self.current_course
        ).count()
        
        completed_lessons = LessonProgress.objects.filter(
            user=self.user,
            lesson__module__course=self.current_course,
            is_completed=True
        ).count()
        
        progress_percentage = (
            (completed_lessons / total_lessons * 100) 
            if total_lessons > 0 else 0
        )
        
        return {
            'current_course': self.current_course.title,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'progress_percentage': round(progress_percentage, 1),
            'time_spent': self.time_spent
        }


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='utilisateur')
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, verbose_name='leçon')
    is_completed = models.BooleanField('est complétée', default=False)
    completed_at = models.DateTimeField('date de complétion', auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"

    class Meta:
        verbose_name = 'Progression de leçon'
        verbose_name_plural = 'Progressions des leçons'
        unique_together = ('user', 'lesson')


class VideoView(models.Model):
    """Modèle pour suivre les vues des vidéos"""
    video = models.ForeignKey('LessonVideo', on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField('adresse IP', null=True, blank=True)
    created_at = models.DateTimeField('date de visualisation', auto_now_add=True)

    class Meta:
        verbose_name = 'Vue vidéo'
        verbose_name_plural = 'Vues vidéo'
        indexes = [
            models.Index(fields=['video', 'user', 'ip_address']),
        ]

    def __str__(self):
        return f"Vue de {self.video.title} par {self.user.username if self.user else self.ip_address}"