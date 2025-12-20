from django.db import models
from django.conf import settings
from courses.models import Course
import uuid


class Certification(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Débutant'),
        ('intermediate', 'Intermédiaire'),
        ('advanced', 'Avancé'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certifications')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certifications')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    code = models.CharField(max_length=64, unique=True, db_index=True, default="", blank=True)
    pdf = models.FileField(upload_to='certificates/', blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'course', 'level')

    def save(self, *args, **kwargs):
        if not self.code:
            # generate a compact unique code
            self.code = uuid.uuid4().hex
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Certif {self.course.title} - {self.level} - {self.user}"

# Create your models here.
