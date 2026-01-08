from django import template
from django.utils.text import capfirst
from django.utils.safestring import mark_safe

register = template.Library()

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
