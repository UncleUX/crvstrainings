from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string
from courses.models import Category


def generate_join_code():
    return get_random_string(8).upper()


class Classroom(models.Model):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='classrooms')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_classrooms')
    join_code = models.CharField(max_length=16, unique=True, default=generate_join_code)
    schedule = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.subject})"


class ClassroomMembership(models.Model):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='classroom_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('classroom', 'user')

    def __str__(self):
        return f"{self.user} in {self.classroom} as {self.role}"


class LiveSession(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200)
    start_at = models.DateTimeField()
    description = models.TextField(blank=True)
    recording_ready = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_at']

    def __str__(self):
        return f"{self.title} @ {self.start_at:%Y-%m-%d %H:%M}"
