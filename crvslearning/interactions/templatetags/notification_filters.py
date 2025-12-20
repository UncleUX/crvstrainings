from django import template
from notifications.models import Notification

register = template.Library()

@register.filter
def unread_notifications(user):
    """Retourne les notifications non lues de l'utilisateur"""
    return user.notifications.filter(is_read=False)

@register.filter
def unread_count(user):
    """Retourne le nombre de notifications non lues de l'utilisateur"""
    return user.notifications.filter(is_read=False).count()
