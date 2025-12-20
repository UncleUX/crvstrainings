from django.urls import path
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from . import views
from .views_learner_tracking import learner_dashboard, course_progress, update_learning_time

app_name = 'users'  # Pense à définir un namespace pour tes URLs

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/instructor/', views.instructor_dashboard, name='instructor_dashboard'),
    path('dashboard/learner/', views.learner_dashboard, name='learner_dashboard'),
    path('profile/', views.my_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    path('profile/upload/avatar/', views.upload_avatar, name='upload_avatar'),
    path('profile/upload/cover/', views.upload_cover, name='upload_cover'),
    path('search/trainers/', views.search_trainers, name='search_trainers'),
    path('instructor/<str:username>/', views.instructor_public, name='instructor_public'),
    path('<str:username>/', views.instructor_public, name='handle_profile'),
    path('learner/<str:username>/', views.learner_public, name='learner_dashboard_handle'),
    
    # URLs pour le suivi des apprenants
    path('tracking/', learner_dashboard, name='learner_tracking'),
    path('tracking/course/<int:course_id>/', course_progress, name='course_progress'),
    path('tracking/update-time/', csrf_exempt(require_POST(update_learning_time)), name='update_learning_time'),
]
