from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Subscription

User = get_user_model()

@receiver(post_save, sender=User)
def create_welcome_subscription(sender, instance, created, **kwargs):
    """
    Crée un abonnement de bienvenue pour les nouveaux utilisateurs (optionnel)
    """
    if created and instance.role == 'learner':
        # Vous pouvez ajouter ici une logique pour s'abonner automatiquement
        # à certains formateurs populaires ou administrateurs
        pass

@receiver(post_save, sender=Subscription)
def send_notification_on_subscription(sender, instance, created, **kwargs):
    """
    Envoie une notification lorsqu'un utilisateur s'abonne à un formateur
    """
    if created:
        # Vous pouvez implémenter ici l'envoi d'une notification
        # par exemple via des webhooks, des emails, ou des notifications en temps réel
        pass
