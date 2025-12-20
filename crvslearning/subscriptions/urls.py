from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # API pour (dés)activer un abonnement
    path('toggle/<str:username>/', 
         views.toggle_subscription, 
         name='toggle_subscription'),
    
    # Vue des abonnements de l'utilisateur connecté
    path('my-subscriptions/', 
         login_required(views.MySubscriptionsView.as_view()), 
         name='my_subscriptions'),
    
    # Vue des abonnés d'un formateur
    path('my-subscribers/', 
         login_required(views.MySubscribersView.as_view()), 
         name='my_subscribers'),
]
