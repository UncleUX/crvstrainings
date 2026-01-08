from django.urls import path
from .views import DocumentationView

app_name = 'documentation'

urlpatterns = [
    path('', DocumentationView.as_view(), name='index'),
]
