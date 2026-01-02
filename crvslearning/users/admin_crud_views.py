from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import admin
from django.urls import reverse
from django.apps import apps
from django.http import HttpResponseForbidden, Http404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.forms import modelform_factory
from django import forms
from django.utils.text import capfirst

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

def get_model_admin(model):
    """Récupère la classe ModelAdmin pour un modèle donné."""
    try:
        return admin.site._registry[model]
    except KeyError:
        return None

def get_model_from_string(app_label, model_name):
    """Récupère un modèle à partir de son app_label et model_name."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        raise Http404("Modèle non trouvé")

@login_required
@admin_required
def model_list(request, app_label, model_name):
    """Affiche la liste des objets d'un modèle."""
    model = get_model_from_string(app_label, model_name)
    model_admin = get_model_admin(model)
    
    if not model_admin:
        raise Http404("Modèle non trouvé dans l'admin")
    
    # Récupérer les objets avec la même logique que l'admin
    queryset = model_admin.get_queryset(request)
    list_display = model_admin.get_list_display(request)
    list_filter = model_admin.get_list_filter(request)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, 25)  # 25 éléments par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': f'Liste des {model._meta.verbose_name_plural}',
        'model': model,
        'model_admin': model_admin,
        'list_display': list_display,
        'page_obj': page_obj,
        'opts': model._meta,
        'has_add_permission': model_admin.has_add_permission(request),
        'has_change_permission': model_admin.has_change_permission(request),
        'has_delete_permission': model_admin.has_delete_permission(request),
    }
    return render(request, 'users/admin/model_list.html', context)

@login_required
@admin_required
def model_add(request, app_label, model_name):
    """Affiche le formulaire d'ajout d'un objet."""
    model = get_model_from_string(app_label, model_name)
    model_admin = get_model_admin(model)
    
    if not model_admin or not model_admin.has_add_permission(request):
        raise Http404("Action non autorisée")
    
    # Créer un formulaire dynamique basé sur le modèle
    ModelForm = modelform_factory(
        model,
        fields='__all__',
        formfield_callback=model_admin.formfield_for_dbfield
    )
    
    if request.method == 'POST':
        form = ModelForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'L\'objet a été ajouté avec succès.')
            return redirect('users:admin_model_list', app_label=app_label, model_name=model_name)
    else:
        form = ModelForm()
    
    context = {
        'title': f'Ajouter {model._meta.verbose_name}',
        'form': form,
        'opts': model._meta,
        'model_admin': model_admin,
        'add': True,
        'change': False,
    }
    return render(request, 'users/admin/change_form.html', context)

@login_required
@admin_required
def model_edit(request, app_label, model_name, object_id):
    """Affiche le formulaire de modification d'un objet."""
    model = get_model_from_string(app_label, model_name)
    model_admin = get_model_admin(model)
    obj = get_object_or_404(model, pk=object_id)
    
    if not model_admin or not model_admin.has_change_permission(request, obj):
        raise Http404("Action non autorisée")
    
    # Créer un formulaire dynamique basé sur le modèle
    ModelForm = modelform_factory(
        model,
        fields='__all__',
        formfield_callback=model_admin.formfield_for_dbfield
    )
    
    if request.method == 'POST':
        form = ModelForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'L\'objet a été modifié avec succès.')
            return redirect('users:admin_model_list', app_label=app_label, model_name=model_name)
    else:
        form = ModelForm(instance=obj)
    
    context = {
        'title': f'Modifier {model._meta.verbose_name}',
        'form': form,
        'opts': model._meta,
        'model_admin': model_admin,
        'original': obj,
        'add': False,
        'change': True,
        'has_delete_permission': model_admin.has_delete_permission(request, obj),
    }
    return render(request, 'users/admin/change_form.html', context)

@login_required
@admin_required
@require_http_methods(["POST"])
def model_delete(request, app_label, model_name, object_id):
    """Supprime un objet."""
    model = get_model_from_string(app_label, model_name)
    model_admin = get_model_admin(model)
    obj = get_object_or_404(model, pk=object_id)
    
    if not model_admin or not model_admin.has_delete_permission(request, obj):
        raise Http404("Action non autorisée")
    
    obj.delete()
    messages.success(request, f'L\'objet a été supprimé avec succès.')
    return redirect('users:admin_model_list', app_label=app_label, model_name=model_name)

@login_required
@admin_required
def admin_dashboard(request):
    """Affiche le tableau de bord administrateur avec les applications et modèles."""
    # Récupérer tous les modèles enregistrés dans l'admin
    app_list = {}
    for model, model_admin in admin.site._registry.items():
        app_label = model._meta.app_label
        if app_label not in app_list:
            app_config = apps.get_app_config(app_label)
            app_list[app_label] = {
                'name': app_config.verbose_name,
                'app_label': app_label,
                'models': []
            }
        
        model_info = {
            'name': model._meta.verbose_name_plural,
            'object_name': model._meta.object_name,
            'admin_url': reverse('users:admin_model_list', kwargs={
                'app_label': model._meta.app_label,
                'model_name': model._meta.model_name
            }),
            'add_url': reverse('users:admin_model_add', kwargs={
                'app_label': model._meta.app_label,
                'model_name': model._meta.model_name
            }),
            'view_only': False,
            'has_add_permission': model_admin.has_add_permission(request),
            'has_change_permission': model_admin.has_change_permission(request),
            'has_delete_permission': model_admin.has_delete_permission(request),
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
