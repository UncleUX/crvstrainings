from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from .models import Subscription

User = get_user_model()


@require_POST
@login_required
def toggle_subscription(request, username):
    """
    Vue pour (dés)activer un abonnement à un formateur
    """
    if request.user.username == username:
        return JsonResponse(
            {'error': _("Vous ne pouvez pas vous abonner à vous-même")}, 
            status=400
        )
    
    trainer = get_object_or_404(User, username=username, role='trainer')
    subscription, created = Subscription.objects.get_or_create(
        subscriber=request.user,
        trainer=trainer,
        defaults={'is_active': True}
    )
    
    if not created:
        subscription.is_active = not subscription.is_active
        subscription.save()
    
    subscribers_count = trainer.subscribers.filter(is_active=True).count()
    
    return JsonResponse({
        'status': 'subscribed' if subscription.is_active else 'unsubscribed',
        'subscribers_count': subscribers_count
    })


class MySubscriptionsView(ListView):
    """Vue pour afficher les abonnements de l'utilisateur connecté"""
    model = Subscription
    template_name = 'subscriptions/my_subscriptions.html'
    context_object_name = 'subscriptions'
    
    def get_queryset(self):
        return (
            Subscription.objects
            .filter(subscriber=self.request.user, is_active=True)
            .select_related('trainer')
        )


class MySubscribersView(ListView):
    """Vue pour afficher les abonnés d'un formateur"""
    model = Subscription
    template_name = 'subscriptions/my_subscribers.html'
    context_object_name = 'subscribers'
    
    def dispatch(self, request, *args, **kwargs):
        # Vérifier que l'utilisateur est un formateur
        if not request.user.is_authenticated or request.user.role != 'trainer':
            messages.warning(
                request, 
                _("Cette page est réservée aux formateurs.")
            )
            return redirect('users:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return (
            Subscription.objects
            .filter(trainer=self.request.user, is_active=True)
            .select_related('subscriber')
        )
