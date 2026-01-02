from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse

class LastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            # Update last_seen at most every minute to reduce writes
            user = request.user
            now = timezone.now()
            try:
                if not user.last_seen or (now - user.last_seen).total_seconds() > 60:
                    type(user).objects.filter(pk=user.pk).update(last_seen=now)
            except Exception:
                pass
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
