from django.utils import timezone

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
