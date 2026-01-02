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


class IsActiveFilter(admin.SimpleListFilter):
    title = 'statut actif'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Actives uniquement'),
            ('0', 'Inactives uniquement'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(is_active=True)
        if self.value() == '0':
            return queryset.filter(is_active=False)
        return queryset

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order', 'is_active', 'created_at')
    list_filter = (IsActiveFilter, 'module', 'created_at')
    list_editable = ('is_active', 'order')
    ordering = ('module', 'order')
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def get_queryset(self, request):
        # Par défaut, n'afficher que les leçons actives
        qs = super().get_queryset(request)
        if not request.GET.get('is_active') and not request.POST.get('action'):
            qs = qs.filter(is_active=True)
        return qs
    
    @admin.action(description='Marquer les leçons sélectionnées comme actives')
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} leçon(s) marquée(s) comme active(s).')
    
    @admin.action(description='Marquer les leçons sélectionnées comme inactives')
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} leçon(s) marquée(s) comme inactive(s).')

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


