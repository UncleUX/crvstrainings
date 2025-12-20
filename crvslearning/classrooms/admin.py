from django.contrib import admin

from .models import Classroom, ClassroomMembership, LiveSession

from .models import Classroom, ClassroomMembership, LiveSession

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "created_by", "join_code", "created_at")
    search_fields = ("name", "subject", "join_code", "created_by__username")
    list_filter = ("created_at",)

@admin.register(ClassroomMembership)
class ClassroomMembershipAdmin(admin.ModelAdmin):
    list_display = ("classroom", "user", "role", "joined_at")
    list_filter = ("role", "joined_at")
    search_fields = ("classroom__name", "user__username")

@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "start_at", "created_at")
    list_filter = ("start_at",)
    search_fields = ("title", "classroom__name")


