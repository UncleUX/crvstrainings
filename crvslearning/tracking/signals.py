from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import ActivityLog
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Récupère l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Enregistre la connexion d'un utilisateur."""
    try:
        ActivityLog.objects.create(
            user=user,
            action='login',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
            timestamp=timezone.now()
        )
        logger.info(f"Connexion enregistrée pour {user.username}")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la connexion: {str(e)}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Enregistre la déconnexion d'un utilisateur."""
    try:
        if user and user.is_authenticated:
            ActivityLog.objects.create(
                user=user,
                action='logout',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                timestamp=timezone.now()
            )
            logger.info(f"Déconnexion enregistrée pour {user.username}")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la déconnexion: {str(e)}")
