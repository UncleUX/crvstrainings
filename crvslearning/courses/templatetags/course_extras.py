from django import template

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
