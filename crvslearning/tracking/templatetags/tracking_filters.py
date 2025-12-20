from django import template

register = template.Library()

@register.filter(name='get_completion_color')
def get_completion_color(percentage):
    """
    Retourne une classe de couleur Bootstrap en fonction du pourcentage de complétion
    """
    if not percentage:
        return 'secondary'
    
    percentage = float(percentage)
    
    if percentage < 25:
        return 'danger'
    elif 25 <= percentage < 50:
        return 'warning'
    elif 50 <= percentage < 75:
        return 'info'
    else:
        return 'success'
