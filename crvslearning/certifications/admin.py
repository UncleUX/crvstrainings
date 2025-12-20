from django.contrib import admin

from .models import Certification

from .models import Certification


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "level", "code", "issued_at", "is_valid")
    list_filter = ("level", "is_valid", "issued_at")
    search_fields = ("code", "user__username", "user__first_name", "user__last_name", "course__title")


