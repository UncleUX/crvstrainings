from django.urls import path
from . import views
from .views_quiz import QuizView

app_name = 'exercises'

urlpatterns = [
    path('lesson/<int:lesson_id>/exercise/new/', views.ExerciseCreateView.as_view(), name='exercise_create'),
    path('exercise/<int:exercise_id>/submit/', views.submit_attempt, name='exercise_submit'),
    path('lesson/<int:lesson_id>/quiz/', QuizView.as_view(), name='lesson_quiz'),
]