from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Subscription

from django.utils.translation import gettext_lazy as _
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'trainer', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = (
        'subscriber__username', 
        'subscriber__email',
        'trainer__username',
        'trainer__email'
    )
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            'fields': ('subscriber', 'trainer', 'is_active')
        }),
        (_('Métadonnées'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)


