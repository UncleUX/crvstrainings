from django.utils import timezone
from .models import ActivityLog
import logging

logger = logging.getLogger(__name__)

class ActivityTrackingMiddleware:
    """
    Middleware pour enregistrer les activités des utilisateurs.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Une réponse par requête
        self._requests = {}

    def __call__(self, request):
        # Vérifier si c'est une requête de connexion ou déconnexion
        if request.path == '/users/login/' and request.method == 'POST':
            # Stocker la requête pour traitement après authentification
            self._requests[id(request)] = request
            request._activity_tracking_middleware = self
        
        # Obtenir la réponse
        response = self.get_response(request)
        
        # Nettoyer
        if id(request) in self._requests:
            del self._requests[id(request)]
            
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Récupère l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_activity(self, user, action, request):
        """Enregistre une activité."""
        try:
            ActivityLog.objects.create(
                user=user,
                action=action,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                timestamp=timezone.now()
            )
            logger.info(f"Activité enregistrée: {user.username} - {action}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'activité: {str(e)}")
