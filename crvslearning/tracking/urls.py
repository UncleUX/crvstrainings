from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    # Tableau de bord de suivi des apprenants
    path('learners/', views.LearnerTrackingView.as_view(), name='learner_tracking'),
    path('learners/<int:learner_id>/', views.learner_detail, name='learner_detail'),
    
    # Tableau de bord de progression des cours
    path('courses/progress/', views.CourseProgressView.as_view(), name='course_progress'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
]
