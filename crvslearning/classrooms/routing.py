from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/classrooms/(?P<classroom_id>\d+)/$", consumers.ClassroomChatConsumer.as_asgi()),
]
