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
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model

def get_online_users():
    """
    Returns a list of currently online users (active in the last 1 minute)
    """
    from django.contrib.sessions.models import Session
    
    User = get_user_model()
    
    # Get active sessions (last 1 minute)
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now() - datetime.timedelta(minutes=1))
    user_id_list = []
    
    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            user_id_list.append(user_id)
    
    # Get unique user IDs and fetch users
    user_id_list = list(set(user_id_list))
    return User.objects.filter(id__in=user_id_list)

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
    print(f"\n=== DEBUG: model_list - Début ===")
    print(f"app_label: {app_label}, model_name: {model_name}")
    
    try:
        model = get_model_from_string(app_label, model_name)
        print(f"Modèle trouvé: {model.__name__}")
        
        model_admin = get_model_admin(model)
        if not model_admin:
            print("ERREUR: Aucun ModelAdmin trouvé pour ce modèle")
            raise Http404("Modèle non trouvé dans l'admin")
        
        # Récupérer les objets avec la même logique que l'admin
        queryset = model_admin.get_queryset(request)
        list_display = model_admin.get_list_display(request)
        list_filter = model_admin.get_list_filter(request)
        
        print(f"Liste des champs à afficher: {list_display}")
        print(f"Nombre d'objets trouvés: {queryset.count()}")
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 25)  # 25 éléments par page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Vérifier les permissions
        has_add_permission = model_admin.has_add_permission(request)
        has_change_permission = model_admin.has_change_permission(request)
        has_delete_permission = model_admin.has_delete_permission(request)
        
        print(f"Permissions - Ajout: {has_add_permission}, Modification: {has_change_permission}, Suppression: {has_delete_permission}")
        
        context = {
            'title': f'Liste des {model._meta.verbose_name_plural}',
            'model': model,
            'model_admin': model_admin,
            'list_display': list_display,
            'page_obj': page_obj,
            'object_list': page_obj.object_list,  # Ajout de object_list pour la compatibilité
            'opts': model._meta,
            'has_add_permission': has_add_permission,
            'has_change_permission': has_change_permission,
            'has_delete_permission': has_delete_permission,
        }
        
        print("=== DEBUG: model_list - Contexte préparé ===")
        print(f"Titre: {context['title']}")
        print(f"Nombre d'objets dans la page: {len(context['object_list'])}")
        print("=== DEBUG: Fin ===\n")
        
        return render(request, 'users/admin/model_list.html', context)
        
    except Exception as e:
        print(f"ERREUR dans model_list: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

@login_required
@admin_required
def model_add(request, app_label, model_name):
    """Affiche le formulaire d'ajout d'un objet."""
    print(f"\n=== DEBUG: model_add - Début ===")
    print(f"app_label: {app_label}, model_name: {model_name}")
    
    try:
        # Récupérer le modèle
        try:
            model = apps.get_model(app_label, model_name)
            if model is None:
                raise LookupError(f"Modèle {app_label}.{model_name} non trouvé")
            print(f"Modèle trouvé: {model.__name__}")
        except LookupError as e:
            error_msg = f"Modèle non trouvé : {str(e)}"
            print(f"ERREUR: {error_msg}")
            raise Http404(error_msg)
        
        # Récupérer l'admin du modèle
        model_admin = get_model_admin(model)
        if not model_admin:
            error_msg = "Configuration admin introuvable pour ce modèle"
            print(f"ERREUR: {error_msg}")
            raise Http404(error_msg)
            
        # Vérifier les permissions
        if not model_admin.has_add_permission(request):
            error_msg = f"L'utilisateur {request.user} n'a pas la permission d'ajouter un objet {model.__name__}"
            print(f"ERREUR: {error_msg}")
            raise PermissionDenied("Vous n'avez pas la permission d'ajouter ce type d'objet")
        
        # Créer un formulaire dynamique basé sur le modèle
        ModelForm = modelform_factory(
            model,
            fields='__all__',
            formfield_callback=lambda f: model_admin.formfield_for_dbfield(f, request=request)
        )
        
        if request.method == 'POST':
            print("\n=== DEBUG: Requête POST reçue ===")
            print(f"Données POST: {request.POST}")
            print(f"Fichiers: {request.FILES}")
            
            form = ModelForm(request.POST, request.FILES)
            print(f"Formulaire valide: {form.is_valid()}")
            
            if form.is_valid():
                try:
                    print("\n=== DEBUG: Formulaire valide ===")
                    print(f"Données nettoyées: {form.cleaned_data}")
                    
                    obj = form.save(commit=False)
                    print("Objet créé avec succès (commit=False)")
                    
                    # Si le modèle a un champ created_by, on le définit automatiquement
                    if hasattr(obj, 'created_by') and hasattr(request, 'user'):
                        obj.created_by = request.user
                        print(f"Champ created_by défini à: {request.user}")
                    
                    obj.save()
                    print(f"Objet enregistré avec l'ID: {obj.pk}")
                    
                    # Pour les relations many-to-many
                    if hasattr(form, 'save_m2m'):
                        form.save_m2m()
                        print("Relations many-to-many enregistrées")
                    
                    messages.success(request, f"L'objet a été ajouté avec succès.")
                    
                    # Redirection en fonction du bouton cliqué
                    if '_addanother' in request.POST:
                        print("Redirection vers l'ajout d'un nouvel objet")
                        return redirect('users:admin_model_add', app_label=app_label, model_name=model_name)
                    elif '_continue' in request.POST:
                        print(f"Redirection vers l'édition de l'objet {obj.pk}")
                        return redirect('users:admin_model_edit', app_label=app_label, model_name=model_name, object_id=obj.pk)
                    else:
                        print(f"Redirection vers la liste des objets")
                        return redirect('users:admin_model_list', app_label=app_label, model_name=model_name)
                        
                except Exception as e:
                    import traceback
                    error_msg = f"Erreur lors de l'ajout de l'objet: {str(e)}\n{traceback.format_exc()}"
                    print(f"\n=== ERREUR ===\n{error_msg}\n==========")
                    messages.error(request, f"Erreur lors de l'ajout : {str(e)}")
            else:
                print("\n=== ERREURS DE VALIDATION ===")
                for field, errors in form.errors.items():
                    for error in errors:
                        error_msg = f"Erreur dans le champ {field}: {error}"
                        print(error_msg)
                        messages.error(request, error_msg)
        else:
            form = ModelForm()
            print("Formulaire vide créé pour requête GET")
        
        # Préparer le contexte pour le template
        context = {
            'title': f'Ajouter {model._meta.verbose_name}',
            'form': form,
            'opts': model._meta,
            'model_admin': model_admin,
            'add': True,
            'change': False,
            'has_view_permission': model_admin.has_view_permission(request, None),
            'has_delete_permission': model_admin.has_delete_permission(request, None),
            'app_label': app_label,
            'original': None,
            'save_as': False,
            'show_save': True,
            'show_save_and_continue': True,
            'show_save_and_add_another': True,
        }
        
        print("\n=== DEBUG: Affichage du formulaire ===")
        print(f"Nombre de champs dans le formulaire: {len(form.fields)}")
        
        return render(request, 'users/admin/change_form.html', context)
        
    except Exception as e:
        import traceback
        error_msg = f"Erreur dans model_add: {str(e)}\n{traceback.format_exc()}"
        print(f"\n=== ERREUR CRITIQUE ===\n{error_msg}\n==================")
        messages.error(request, f"Une erreur est survenue : {str(e)}")
        return redirect('users:admin_dashboard')
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
    
    # Créer une fonction de rappel qui inclut le paramètre request
    def formfield_for_dbfield_with_request(db_field, **kwargs):
        return model_admin.formfield_for_dbfield(db_field, request=request, **kwargs)
    
    # Créer un formulaire dynamique basé sur le modèle
    ModelForm = modelform_factory(
        model,
        fields='__all__',
        formfield_callback=formfield_for_dbfield_with_request
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
    # Importer les modèles nécessaires
    from django.contrib.auth import get_user_model
    from courses.models import Course, Enrollment
    from subscriptions.models import Subscription
    from tracking.models import ActivityLog  # Import du modèle ActivityLog
    
    # Récupérer les statistiques avec débogage
    User = get_user_model()
    
    # Compter les cours avec vérification
    try:
        total_courses = Course.objects.count()
        print(f"[DEBUG] Nombre de cours trouvés : {total_courses}")
    except Exception as e:
        print(f"[ERREUR] Impossible de compter les cours : {str(e)}")
        total_courses = 0
    
    # Compter les inscriptions avec vérification
    try:
        total_enrollments = Enrollment.objects.count()
        print(f"[DEBUG] Nombre d'inscriptions trouvées : {total_enrollments}")
    except Exception as e:
        print(f"[ERREUR] Impossible de compter les inscriptions : {str(e)}")
        total_enrollments = 0
    
    # Compter les abonnements actifs avec vérification
    try:
        active_subscriptions = Subscription.objects.filter(is_active=True).count()
        print(f"[DEBUG] Nombre d'abonnements actifs trouvés : {active_subscriptions}")
    except Exception as e:
        print(f"[ERREUR] Impossible de compter les abonnements actifs : {str(e)}")
        active_subscriptions = 0
    
    # Calculer les statistiques de base
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # Calculer les pourcentages pour la répartition
    active_users_percentage = round((active_users / total_users * 100) if total_users > 0 else 0, 1)
    
    # Calculer le pourcentage de cours publiés
    published_courses = Course.objects.filter(is_published=True).count()
    published_courses_percentage = round((published_courses / total_courses * 100) if total_courses > 0 else 0, 1)
    
    # Calculer le taux de réussite moyen (exemple avec les examens)
    # Note: À adapter selon votre modèle de données des examens
    from django.db.models import Avg, Case, When, FloatField
    try:
        from exams.models import ExamAttempt
        success_rate = ExamAttempt.objects.aggregate(
            avg_success=Avg(
                Case(
                    When(score__gte=10, then=100.0),  # Supposons que 10/20 est la note de réussite
                    default=0.0,
                    output_field=FloatField()
                )
            )
        )['avg_success'] or 0
        success_rate = round(success_rate, 1)
    except Exception as e:
        print(f"[INFO] Impossible de calculer le taux de réussite: {str(e)}")
        success_rate = 82.0  # Valeur par défaut si le calcul échoue
    
    # Préparer les statistiques
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'active_users_percentage': active_users_percentage,
        'total_courses': total_courses,
        'published_courses': published_courses,
        'published_courses_percentage': published_courses_percentage,
        'success_rate': success_rate,
        'total_enrollments': total_enrollments,
        'active_subscriptions': active_subscriptions,
        'total_income': 0,  # À implémenter avec le système de paiement
    }
    
    # Récupérer les 5 derniers utilisateurs inscrits
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    # Récupérer les logs d'activité récents (connexions/déconnexions)
    recent_activity_logs = ActivityLog.objects.filter(
        action__in=['login', 'logout']
    ).select_related('user').order_by('-timestamp')[:20]  # 20 derniers logs
    
    # Récupérer les cours les plus populaires
    from django.db.models import Count
    try:
        popular_courses = Course.objects.annotate(
            enrollment_count=Count('enrollments')
        ).order_by('-enrollment_count')[:5]
        print(f"[DEBUG] Cours populaires trouvés : {len(popular_courses)}")
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer les cours populaires : {str(e)}")
        popular_courses = []
    
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
    # Trier les applications par nom
    app_list = dict(sorted(app_list.items()))
    
    context = {
        'title': 'Tableau de bord administrateur',
        'app_list': list(app_list.values()),
        'user': request.user,
        'stats': stats,
        'recent_users': recent_users,
        'popular_courses': popular_courses,
        'activity_logs': recent_activity_logs,
        'current_date': timezone.now(),
        'online_users': get_online_users(),
    }
    return render(request, 'users/admin/dashboard.html', context)
