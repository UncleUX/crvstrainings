from django import template
from django.utils.text import capfirst
from django.utils.safestring import mark_safe
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

@register.filter
def field_verbose_name(obj, field_name):
    """
    Retourne le nom d'affichage d'un champ de modèle.
    Usage: {{ model|field_verbose_name:"field_name" }}
    """
    try:
        return obj._meta.get_field(field_name).verbose_name
    except (AttributeError, KeyError):
        return field_name.replace('_', ' ').title()

@register.filter
def get_attr(obj, attr_name):
    """
    Récupère un attribut d'un objet en utilisant son nom sous forme de chaîne.
    Usage: {{ object|get_attr:"attribute_name" }}
    """
    if hasattr(obj, str(attr_name)):
        return getattr(obj, attr_name)
    elif hasattr(obj, 'get') and callable(getattr(obj, 'get')):
        return obj.get(attr_name, '')
    return ''

@register.filter
def format_value(value):
    """
    Formate la valeur pour l'affichage dans le tableau.
    """
    if value is None:
        return '-' 
    if isinstance(value, bool):
        return 'Oui' if value else 'Non'
    if hasattr(value, 'strftime'):
        return value.strftime('%d/%m/%Y %H:%M')
    return str(value)
