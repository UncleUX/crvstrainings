from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a value from a dictionary using a variable as key.
    Usage: {{ my_dict|get_item:my_key }}
    """
    return dictionary.get(key, None)
