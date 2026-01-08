from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
import json

class LastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            user = request.user
            now = timezone.now()
            
            # Mettre à jour le last_seen toutes les 30 secondes maximum
            if not user.last_seen or (now - user.last_seen).total_seconds() > 30:
                user.last_seen = now
                user.save(update_fields=['last_seen'])
            
            # Mettre à jour le cache des utilisateurs en ligne
            cache_key = f'user_online_{user.id}'
            user_data = {
                'id': user.id,
                'username': user.username,
                'last_seen': now.isoformat(),
                'is_online': True
            }
            cache.set(cache_key, json.dumps(user_data), 60 * 5)  # 5 minutes d'expiration
        
        return response


class AdminRedirectMiddleware:
    """
    Redirige automatiquement les administrateurs vers le tableau de bord admin
    lorsqu'ils se connectent via la page de connexion normale.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier si l'utilisateur est un administrateur et s'il est sur la page d'accueil
        if (request.user.is_authenticated and 
            request.user.is_staff and 
            request.path == '/' and 
            not request.path.startswith('/admin/') and
            not request.path.startswith('/users/admin/') and
            not request.path.startswith('/static/') and
            not request.path.startswith('/media/')):
            return redirect('users:admin_dashboard')
            
        return self.get_response(request)
