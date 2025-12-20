from django.contrib import admin
from crvslearning.admin import admin_site

# Remplacer admin.site par admin_site
admin.site = admin_site

from crvslearning import admin_site

# Remplacer admin.site par admin_site
admin.site = admin_site

from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'recipient', 'sent_at', 'read_at')
    list_filter = ('sent_at', 'read_at')
    search_fields = ('subject', 'body', 'sender__username', 'recipient__username')

