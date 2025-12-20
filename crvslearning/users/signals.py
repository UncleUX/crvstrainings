from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from courses.models import LearningPath

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_learning_path(sender, instance, created, **kwargs):
    """
    Crée automatiquement un LearningPath lorsqu'un nouvel utilisateur est créé
    """
    if created and not hasattr(instance, 'learning_path'):
        LearningPath.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_learning_path(sender, instance, **kwargs):
    """
    Sauvegarde le LearningPath lors de la mise à jour de l'utilisateur
    """
    if hasattr(instance, 'learning_path'):
        instance.learning_path.save()
