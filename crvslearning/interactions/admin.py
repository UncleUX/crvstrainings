from django.contrib import admin

from .models import ChatRoom, ChatMessage, Notification

from .models import ChatRoom, ChatMessage, Notification

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('roomId', 'type', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('roomId', 'name')
    filter_horizontal = ('members',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'timestamp', 'read')
    list_filter = ('read', 'timestamp')
    search_fields = ('message', 'sender__username')
    date_hierarchy = 'timestamp'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'notification_type', 'read', 'created_at')
    list_filter = ('read', 'notification_type', 'created_at')
    search_fields = ('recipient__username', 'message')
    date_hierarchy = 'created_at'


