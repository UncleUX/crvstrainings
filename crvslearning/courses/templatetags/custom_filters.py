from django import template
from notifications.models import Notification

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to access dictionary values by key.
    Usage: {{ my_dict|get_item:key }}
    """
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def unread_notifications(user):
    """
    Returns unread notifications for a user.
    Usage: {{ user|unread_notifications }}
    """
    if not hasattr(user, 'notifications'):
        return []
    return user.notifications.filter(is_read=False)

@register.filter
def unread_count(user):
    """
    Returns the count of unread notifications for a user.
    Usage: {{ user|unread_count }}
    """
    if not hasattr(user, 'notifications'):
        return 0
    return user.notifications.filter(is_read=False).count()
