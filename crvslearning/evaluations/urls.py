from django.urls import path
from . import views

app_name = 'evaluations'

urlpatterns = [
    path('courses/<int:course_id>/levels/<str:level>/evaluation/', views.start_evaluation, name='start_level_evaluation'),
]
