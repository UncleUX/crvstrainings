from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    # URLs pour les messages
    path('messages/inbox/', views.InboxView.as_view(), name='inbox'),
    path('messages/compose/', views.ComposeView.as_view(), name='compose'),
    path('messages/send/<int:recipient_id>/', views.send_message, name='send_message'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='view_message'),
    path('messages/<int:pk>/delete/', views.MessageDeleteView.as_view(), name='delete_message'),
    path('conversation/<int:user_id>/', views.ConversationView.as_view(), name='conversation'),
    
    # URLs pour les notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # API
    path('api/unread-count/', views.get_unread_count, name='unread_count'),
]