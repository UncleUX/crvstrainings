import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async

from .models import Classroom, ClassroomMembership


class ClassroomChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.classroom_id = self.scope['url_route']['kwargs'].get('classroom_id')
        self.room_group_name = f'classroom_{self.classroom_id}'

        user = self.scope.get('user') or AnonymousUser()
        is_allowed = await self._user_allowed(user, self.classroom_id)
        if not user.is_authenticated or not is_allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': json.dumps({'system': True, 'text': f"{user.username} a rejoint la discussion."})
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope.get('user')
        try:
            data = json.loads(text_data or '{}')
            text = (data.get('text') or '').strip()
        except Exception:
            text = ''
        if not text:
            return
        payload = {
            'type': 'chat.message',
            'message': json.dumps({'user': user.username, 'text': text})
        }
        await self.channel_layer.group_send(self.room_group_name, payload)

    async def chat_message(self, event):
        await self.send(text_data=event['message'])

    @database_sync_to_async
    def _user_allowed(self, user, classroom_id):
        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            return False
        if not user.is_authenticated:
            return False
        if classroom.created_by_id == user.id:
            return True
        return ClassroomMembership.objects.filter(classroom_id=classroom_id, user=user).exists()
