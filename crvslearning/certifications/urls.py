from django.urls import path
from . import views

app_name = 'certifications'

urlpatterns = [
    path('verify/<str:code>/', views.verify, name='verify'),
    path('achievements/', views.achievements, name='achievements'),
]
