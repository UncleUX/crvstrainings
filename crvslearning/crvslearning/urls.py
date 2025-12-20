from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.shortcuts import redirect
from users import views as user_views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', lambda request: redirect('users:login'), name='home'),
    path('accueil/', include('courses.urls')),
    path('evaluations/', include('evaluations.urls')),
    path('certifications/', include('certifications.urls')),
    # Ajoutez cette ligne dans urlpatterns
    path('chat/', include('interactions.urls', namespace='interactions')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('classrooms/', include('classrooms.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    path('exercices/', include('exercices.urls', namespace='exercises')),
    path('sms/', include('sms.urls', namespace='sms')),
    path('tracking/', include('tracking.urls', namespace='tracking')),
    path('dashboard/', lambda request: redirect('courses:all_courses')),
    re_path(r'^@(?P<username>[\w.@+-]+)/$', user_views.instructor_public, name='handle_profile'),
    re_path(r'^@(?P<username>[\w.@+-]+)/dashboard/$', user_views.learner_dashboard_handle, name='learner_dashboard_handle'),
    re_path(r'^~(?P<username>[\w.@+-]+)/$', user_views.learner_public, name='learner_handle'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)