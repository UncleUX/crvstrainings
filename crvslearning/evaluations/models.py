from django.db import models
from django.conf import settings
from courses.models import Course


class EvaluationLevel(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Débutant'),
        ('intermediate', 'Intermédiaire'),
        ('advanced', 'Avancé'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='evaluations')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    title = models.CharField(max_length=255)
    threshold = models.PositiveIntegerField(default=70)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('course', 'level')

    def __str__(self):
        return f"{self.course.title} - {self.level}"


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='evaluation_attempts')
    evaluation = models.ForeignKey(EvaluationLevel, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField()
    passed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.evaluation} - {self.score}"

class EvaluationQuestion(models.Model):
    evaluation = models.ForeignKey(EvaluationLevel, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"  # noqa


class EvaluationChoice(models.Model):
    question = models.ForeignKey(EvaluationQuestion, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.text} ({'✓' if self.is_correct else '✗'})"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(EvaluationQuestion, on_delete=models.CASCADE)
    choice = models.ForeignKey(EvaluationChoice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"Attempt#{self.attempt_id} - Q{self.question_id} -> {self.choice_id}"
