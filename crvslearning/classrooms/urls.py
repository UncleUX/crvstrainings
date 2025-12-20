from django.urls import path
from . import views

app_name = 'classrooms'

urlpatterns = [
    path('', views.my_classrooms, name='my_classrooms'),
    path('create/', views.classroom_create, name='create'),
    path('join/', views.join_by_code, name='join'),
    path('recording/webhook/', views.recording_webhook, name='recording_webhook'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:session_id>/start/', views.session_start, name='session_start'),
    path('sessions/<int:session_id>/join/', views.session_join, name='session_join'),
    path('<int:classroom_id>/', views.classroom_detail, name='detail'),
]
