from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib import admin, messages
from django.urls import reverse
from django.apps import apps
from django.views.decorators.cache import never_cache
from django.http import JsonResponse, HttpResponseForbidden
from courses.forms import CourseForm
from courses.models import Category

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
    # Gestion du formulaire de création de cours
    course_form = CourseForm(request.POST or None, request.FILES or None)
    
    if request.method == 'POST' and 'create_course' in request.POST:
        if course_form.is_valid():
            course = course_form.save(commit=False)
            course.created_by = request.user
            
            # Gestion de la catégorie
            category_id = request.POST.get('category')
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    course.category = category
                except Category.DoesNotExist:
                    pass
                    
            course.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Cours créé avec succès.',
                    'redirect_url': reverse('courses:course_detail', kwargs={'course_id': course.id})
                })
                
            messages.success(request, "Cours créé avec succès.")
            return redirect('courses:course_detail', course_id=course.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'form_errors': course_form.errors,
                    'message': 'Veuillez corriger les erreurs ci-dessous.'
                }, status=400)
                
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    
    # Récupérer tous les modèles enregistrés dans l'admin
    app_list = {}
    print("\n=== DEBUG: Modèles enregistrés dans l'admin ===")
    for model, model_admin in admin.site._registry.items():
        print(f"- {model._meta.app_label}.{model._meta.model_name}")
        app_label = model._meta.app_label
        if app_label not in app_list:
            app_config = apps.get_app_config(app_label)
            app_list[app_label] = {
                'name': app_config.verbose_name,
                'app_url': reverse('admin:app_list', kwargs={'app_label': app_label}),
                'models': []
            }
        
        # Créer les URLs d'administration de manière absolue
        admin_base = reverse('admin:index')
        model_info = {
            'name': model._meta.verbose_name_plural,
            'object_name': model._meta.object_name,
            'admin_url': f"{admin_base}{model._meta.app_label}/{model._meta.model_name}/",
            'add_url': f"{admin_base}{model._meta.app_label}/{model._meta.model_name}/add/",
            'view_only': False
        }
        app_list[app_label]['models'].append(model_info)
    
    # Trier les applications et les modèles
    app_list = dict(sorted(app_list.items()))
    for app in app_list.values():
        app['models'].sort(key=lambda x: x['name'])
    
    # Debug: Afficher le contenu de app_list dans la console serveur
    import pprint
    print("\n=== DEBUG: Contenu de app_list ===")
    pprint.pprint(app_list)
    print("=== FIN DU DEBUG ===\n")
    
    # Récupérer les catégories pour le formulaire
    categories = Category.objects.all().order_by('name')
    
    # Récupérer les logs d'activité (connexions/déconnexions)
    from tracking.models import ActivityLog
    from django.utils import timezone
    from django.db.models import Q
    
    # Récupérer les logs d'activité
    activity_logs = ActivityLog.objects.filter(
        action__in=['login', 'logout']
    ).select_related('user').order_by('-timestamp')[:10]
    
    # Récupérer les utilisateurs actifs (connectés dans les 5 dernières minutes)
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    
    # Récupérer tous les utilisateurs avec une activité récente
    active_users = request.user.__class__.objects.filter(
        last_seen__isnull=False
    ).order_by('-last_seen')
    
    # Marquer les utilisateurs en ligne
    for user in active_users:
        cache_key = f'user_online_{user.id}'
        user_data = cache.get(cache_key)
        user.is_currently_online = bool(user_data)
    
    # Séparer les utilisateurs en ligne et hors ligne
    online_users = [u for u in active_users if u.is_currently_online]
    offline_users = [u for u in active_users if not u.is_currently_online]
    
    # Combiner les listes (en ligne d'abord, puis hors ligne)
    all_users = online_users + offline_users
    
    # Utiliser les utilisateurs déjà récupérés et marqués
    active_users = all_users[:10]  # Limiter aux 10 premiers

    # Préparer la liste des applications pour le template
    app_list_for_template = []
    if app_list:
        app_list_for_template = list(app_list.values())
        print("\n=== DEBUG: Liste des applications pour le template ===")
        for app in app_list_for_template:
            print(f"- {app['name']} ({len(app['models'])} modèles)")
    else:
        print("\n=== ATTENTION: Aucune application trouvée dans app_list ===")
    
    context = {
        'title': 'Tableau de bord administrateur',
        'app_list': app_list_for_template,  # Utiliser la liste préparée
        'user': request.user,
        'course_form': course_form,
        'categories': categories,
        'activity_logs': activity_logs,
        'online_users': online_users,
        'active_users': active_users,  # 10 derniers utilisateurs actifs (en ligne d'abord)
        'all_active_users': all_users,  # Tous les utilisateurs actifs
    }
    
    # Si c'est une requête AJAX pour le chargement initial du formulaire
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'get_form' in request.GET:
        # Préparer les données des catégories pour le JSON
        categories_data = [{'id': cat.id, 'name': cat.name} for cat in categories]
        
        return JsonResponse({
            'form_html': render_to_string('users/admin/partials/course_form.html', context, request=request),
            'categories': categories_data
        })
    
    return render(request, 'users/admin/dashboard.html', context)
