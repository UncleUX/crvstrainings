from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import admin
from django.urls import reverse
from django.apps import apps
from django.http import HttpResponseForbidden
from django.views.decorators.cache import never_cache

def admin_required(view_func):
    """
    Vérifie que l'utilisateur est un administrateur.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if not request.user.is_staff:
            return HttpResponseForbidden("Accès refusé. Vous n'avez pas les droits d'administration.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@admin_required
@never_cache
def admin_dashboard(request):
    # Récupérer tous les modèles enregistrés dans l'admin
    app_list = {}
    for model, model_admin in admin.site._registry.items():
        app_label = model._meta.app_label
        if app_label not in app_list:
            app_config = apps.get_app_config(app_label)
            app_list[app_label] = {
                'name': app_config.verbose_name,
                'app_url': reverse('admin:app_list', kwargs={'app_label': app_label}),
                'models': []
            }
        
        model_info = {
            'name': model._meta.verbose_name_plural,
            'object_name': model._meta.object_name,
            'admin_url': reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist'),
            'add_url': reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_add'),
            'view_only': False
        }
        app_list[app_label]['models'].append(model_info)
    
    # Trier les applications et les modèles
    app_list = dict(sorted(app_list.items()))
    for app in app_list.values():
        app['models'].sort(key=lambda x: x['name'])
    
    context = {
        'title': 'Tableau de bord administrateur',
        'app_list': list(app_list.values()),
        'user': request.user,
    }
    return render(request, 'users/admin/dashboard.html', context)
