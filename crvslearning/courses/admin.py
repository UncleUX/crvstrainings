from django.apps import apps
from django.contrib import admin

# Utiliser l'admin par défaut de Django

from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered
from .models import Course, Module, Lesson, UserLessonProgress, Category, Enrollment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')                # Affiche Name et Slug dans la liste
    prepopulated_fields = {"slug": ("name",)}     # Remplit automatiquement Slug à partir de Name


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'language', 'created_by', 'created_at')
    search_fields = ('title', 'category__name', 'language')  # ici, j'ai corrigé 'category' -> 'category__name' pour FK
    list_filter = ('language', 'category', 'created_at')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'level', 'order')
    list_filter = ('course', 'level')
    ordering = ('course', 'order')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')
    list_filter = ('module',)
    ordering = ('module', 'order')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at')
    list_filter = ('enrolled_at', 'course')
    search_fields = ('user__username', 'course__title')

@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'completed_at')
    search_fields = ('user__username', 'lesson__title')

# Auto-register any other models in the app without a custom admin
app_config = apps.get_app_config('courses')
for model in app_config.get_models():
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass


