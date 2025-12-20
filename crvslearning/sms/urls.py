from django.urls import path
from . import views

app_name = 'sms'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('chat/<int:user_id>/', views.chat, name='chat'),
    path('send/<int:user_id>/', views.send_message, name='send_message'),
    path('get-new-messages/<int:user_id>/<int:last_message_id>/', 
         views.get_new_messages, name='get_new_messages'),
]
