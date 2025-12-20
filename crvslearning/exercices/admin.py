from django.contrib import admin

from .models import Exercise, Choice, UserExerciseAttempt

from .models import Exercise, Choice, UserExerciseAttempt

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('question', 'lesson', 'order', 'created_at')
    list_filter = ('lesson__module__course', 'lesson')
    search_fields = ('question',)
    inlines = [ChoiceInline]

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('text', 'exercise', 'is_correct', 'order')
    list_filter = ('is_correct', 'exercise__lesson__module__course')
    search_fields = ('text', 'exercise__question')

@admin.register(UserExerciseAttempt)
class UserExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'exercise__lesson__module__course')
    search_fields = ('user__username', 'exercise__question')

