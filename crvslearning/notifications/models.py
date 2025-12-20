from django.db import models
from django.contrib.auth import get_user_model

# Obtenez le modèle User personnalisé
User = get_user_model()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification pour {self.user.username}: {self.message[:50]}..."