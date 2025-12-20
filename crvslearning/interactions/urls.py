from django.urls import path
from . import views
from django.views.generic import RedirectView
from .views import GlobalChatView

app_name = 'interactions'

urlpatterns = [
    # Chat URLs
    path('chat-global/', GlobalChatView.as_view(), name='chat_global'),
    path('inbox/', views.inbox, name='inbox'),
    path('compose/', views.compose, name='compose'),
    path('compose/<str:recipient_username>/', views.compose, name='compose_to'),
    path('conversation/<int:user_id>/', views.conversation, name='conversation'),
    path('send-message/<int:recipient_id>/', views.send_message, name='send_message'),
    
    # Notifications URLs
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # API URLs
    path('api/chats/', views.ChatRoomView.as_view(), name='chat_room_list'),
    path('api/chats/<int:pk>/', views.ChatRoomDetailView.as_view(), name='chat_room_detail'),
    path('api/messages/', views.MessageListCreateView.as_view(), name='message_list_create'),
    path('api/messages/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('api/notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('api/notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notification_detail'),
]
