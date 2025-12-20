from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Lesson

User = get_user_model()

class Exercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='exercises')
    question = models.TextField(verbose_name="Question")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Exercice"
        verbose_name_plural = "Exercices"

    def __str__(self):
        return f"Exercice {self.order} - {self.question[:50]}..."

class Choice(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500, verbose_name="Texte de la réponse")
    is_correct = models.BooleanField(default=False, verbose_name="Réponse correcte")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    explanation = models.TextField(blank=True, null=True, verbose_name="Explication")

    class Meta:
        ordering = ['order']
        verbose_name = "Choix"
        verbose_name_plural = "Choix"

    def __str__(self):
        return f"{self.text[:50]}... ({'✓' if self.is_correct else '✗'})"

class UserExerciseAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_attempts')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='user_attempts')
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tentative d'exercice"
        verbose_name_plural = "Tentatives d'exercices"
        unique_together = ('user', 'exercise')

    def __str__(self):
        return f"{self.user.username} - {self.exercise} - {'✓' if self.is_correct else '✗'}"