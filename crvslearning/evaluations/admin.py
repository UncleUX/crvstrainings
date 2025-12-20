from django.contrib import admin

from .models import EvaluationLevel, Attempt, EvaluationQuestion, EvaluationChoice, AttemptAnswer


class EvaluationChoiceInline(admin.TabularInline):
    model = EvaluationChoice
    extra = 2


class EvaluationQuestionInline(admin.StackedInline):
    model = EvaluationQuestion
    extra = 1
    show_change_link = True


@admin.register(EvaluationQuestion)
class EvaluationQuestionAdmin(admin.ModelAdmin):
    list_display = ("evaluation", "order", "text", "points")
    list_filter = ("evaluation",)
    inlines = [EvaluationChoiceInline]


@admin.register(EvaluationLevel)
class EvaluationLevelAdmin(admin.ModelAdmin):
    list_display = ("course", "level", "title", "threshold", "is_active")
    list_filter = ("course", "level", "is_active")
    inlines = [EvaluationQuestionInline]


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    can_delete = False
    readonly_fields = ("question", "choice")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "evaluation", "score", "passed", "created_at")
    list_filter = ("evaluation", "passed")
    readonly_fields = ("user", "evaluation", "score", "passed", "created_at")
    inlines = [AttemptAnswerInline]


