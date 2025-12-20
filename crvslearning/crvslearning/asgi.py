"""
ASGI config for crvslearning project (Channels-enabled).
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crvslearning.settings')

django_asgi_app = get_asgi_application()

# Importer les URLs WebSocket des différentes applications
try:
    from classrooms.routing import websocket_urlpatterns as classroom_ws
except Exception:
    classroom_ws = []

try:
    from core.routing import websocket_urlpatterns as core_ws
except Exception:
    core_ws = []

# Combiner toutes les URLs WebSocket
websocket_urlpatterns = classroom_ws + core_ws

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
