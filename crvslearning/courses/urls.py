from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.all_courses, name='all_courses'),  # page d'accueil des cours
    path('search/', views.search, name='search'),
    path('search/suggest/', views.search_suggest, name='search_suggest'),
    path('api/my-courses/', views.api_my_courses, name='api_my_courses'),
    path('api/courses/<int:course_id>/modules/', views.api_modules_for_course, name='api_modules_for_course'),
    path('api/modules/<int:module_id>/lessons/', views.api_lessons_for_module, name='api_lessons_for_module'),
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('<int:course_id>/modules/', views.module_list, name='module_list'),
    path('lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lessons/<int:lesson_id>/videos/create/', views.lesson_video_create, name='lesson_video_create'),
    path('lessons/<int:lesson_id>/complete/', views.mark_lesson_completed, name='mark_lesson_completed'),
    path('<int:course_id>/modules/<int:module_id>/complete/', views.mark_module_completed, name='mark_module_completed'),
    path('<int:course_id>/complete/', views.mark_course_completed, name='mark_course_completed'),
    path('lessons/<int:lesson_id>/comment/', views.add_comment, name='add_comment'),
    path('<int:course_id>/rate/', views.rate_course, name='rate_course'),
    path('<int:course_id>/like/', views.toggle_like, name='toggle_like'),

    # Vues pour formateurs (création/gestion)
    path('manage/', views.course_list, name='manage'),
    path('create/', views.course_create, name='course_create'),
    path('categories/create/', views.create_category, name='create_category'),
    path('<int:course_id>/modules/<int:module_id>/', views.module_detail, name='module_detail'),
    path('<int:course_id>/modules/create/', views.module_create, name='module_create'),
    path('<int:course_id>/modules/<int:module_id>/lessons/create/', views.lesson_create, name='lesson_create'),


]
