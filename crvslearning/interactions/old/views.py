from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from notifications.models import Notification
from .models import Message
from .forms import MessageForm
from django.urls import reverse

User = get_user_model()

@login_required
def send_message(request, recipient_id):
    recipient = get_object_or_404(User, id=recipient_id)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.save()
            
            # Créer une notification
            Notification.objects.create(
                user=recipient,
                message=f"Vous avez reçu un nouveau message de {request.user.get_full_name()}",
                url=reverse('interactions:conversation', kwargs={'user_id': request.user.id})
            )
            
            return JsonResponse({
                'success': True,
                'message_id': message.id,
                'body': message.body,
                'sent_at': message.sent_at.strftime('%H:%M'),
                'sender_id': message.sender.id
            })
        return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)

# @login_required
# def send_message(request, recipient_id):
#     recipient = get_object_or_404(User, id=recipient_id)
    
#     if request.method == 'POST':
#         form = MessageForm(request.POST)
#         if form.is_valid():
#             message = form.save(commit=False)
#             message.sender = request.user
#             message.recipient = recipient
#             message.save()
            
#             # Créer une notification
#             Notification.objects.create(
#                 user=recipient,
#                 message=f"Vous avez reçu un nouveau message de {request.user.get_full_name()}",
#                 url=f"/interactions/messages/{message.id}/"
#             )
            
#             django_messages.success(request, 'Message envoyé avec succès!')
#             return redirect('subscriptions:my_subscribers')
    
#     form = MessageForm()
#     return render(request, 'interactions/send_message.html', {
#         'form': form,
#         'recipient': recipient
#     })

@login_required
def notifications(request):
    """Affiche la liste des notifications de l'utilisateur connecté"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'interactions/notifications.html', {
        'notifications': notifications
    })

@login_required
def mark_notification_read(request, notification_id):
    """Marque une notification comme lue et redirige vers l'URL associée"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    # Marquer comme lue
    notification.is_read = True
    notification.save()
    
    # Rediriger vers l'URL de la notification
    return redirect(notification.url if notification.url else 'interactions:notifications')


class InboxView(LoginRequiredMixin, ListView):
    model = Message
    template_name = 'interactions/inbox.html'
    context_object_name = 'messages'
    paginate_by = 20
    
    def get_queryset(self):
        tab = self.request.GET.get('tab', 'inbox')
        user = self.request.user
        
        if tab == 'sent':
            # Dernier message de chaque conversation où l'utilisateur est l'expéditeur
            from django.db.models import Max, Count, Case, When, Value, IntegerField
            
            # Récupère les derniers messages envoyés groupés par destinataire
            sent_messages = Message.objects.filter(sender=user).values('recipient').annotate(
                latest_message=Max('sent_at')
            ).order_by('-latest_message')
            
            # Récupère les messages complets correspondants
            messages = []
            for msg in sent_messages:
                message = Message.objects.filter(
                    sender=user,
                    recipient_id=msg['recipient'],
                    sent_at=msg['latest_message']
                ).first()
                if message:
                    message.other_user = message.recipient
                    messages.append(message)
            return messages
            
        elif tab == 'unread':
            # Messages non lus groupés par expéditeur
            unread_messages = Message.objects.filter(
                recipient=user, 
                is_read=False
            ).order_by('-sent_at')
            
            # On ajoute une référence à l'autre utilisateur pour le regroupement
            for msg in unread_messages:
                msg.other_user = msg.sender
                msg.unread_count = Message.objects.filter(
                    sender=msg.sender, 
                    recipient=user,
                    is_read=False
                ).count()
            return unread_messages
            
        else:
            # Boîte de réception - Dernier message de chaque conversation
            from django.db.models import Max, Count, Case, When, Value, IntegerField
            
            # Récupère les derniers messages reçus groupés par expéditeur
            received_messages = Message.objects.filter(recipient=user).values('sender').annotate(
                latest_message=Max('sent_at')
            ).order_by('-latest_message')
            
            # Récupère les messages complets correspondants
            messages = []
            for msg in received_messages:
                message = Message.objects.filter(
                    sender_id=msg['sender'],
                    recipient=user,
                    sent_at=msg['latest_message']
                ).first()
                if message:
                    message.other_user = message.sender
                    # Compte les messages non lus de cet expéditeur
                    message.unread_count = Message.objects.filter(
                        sender=message.sender,
                        recipient=user,
                        is_read=False
                    ).count()
                    messages.append(message)
            return messages
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['current_tab'] = self.request.GET.get('tab', 'inbox')
        context['inbox_count'] = Message.objects.filter(recipient=user).count()
        context['sent_count'] = Message.objects.filter(sender=user).count()
        context['unread_count'] = Message.objects.filter(recipient=user, is_read=False).count()
        return context

    def form_valid(self, form):
        form.instance.sender = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        # Utiliser le bon nom de paramètre 'pk' au lieu de 'message_id'
        return reverse('interactions:view_message', kwargs={'pk': self.object.pk})


from django.urls import reverse, reverse_lazy
from django.contrib import messages as django_messages
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from notifications.models import Notification

class ComposeView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'interactions/compose.html'
    success_url = reverse_lazy('interactions:inbox')

    def form_valid(self, form):
        form.instance.sender = self.request.user
        response = super().form_valid(form)
        
        # Créer une notification pour le destinataire
        Notification.objects.create(
            user=self.object.recipient,
            message=f"Vous avez reçu un nouveau message de {self.request.user.get_full_name()}",
            url=reverse('interactions:view_message', kwargs={'pk': self.object.id})
        )
        
        django_messages.success(self.request, 'Message envoyé avec succès!')
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('interactions:view_message', kwargs={'pk': self.object.pk})

class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = 'interactions/message_detail.html'
    context_object_name = 'message'
    # Supprimez la ligne suivante car nous utilisons le paramètre par défaut 'pk'
    # pk_url_kwarg = 'message_id'

    def get_queryset(self):
        # Ne montrer que les messages reçus ou envoyés par l'utilisateur
        qs = super().get_queryset()
        return qs.filter(
            Q(recipient=self.request.user) | 
            Q(sender=self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Marquer le message comme lu s'il est destiné à l'utilisateur actuel
        message = self.get_object()
        if message.recipient == self.request.user and not message.is_read:
            message.mark_as_read()
        return context

class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    pk_url_kwarg = 'message_id'
    success_url = reverse_lazy('interactions:inbox')

    def get_queryset(self):
        # Ne permettre la suppression que pour le destinataire
        return Message.objects.filter(recipient=self.request.user)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        django_messages.success(request, 'Message supprimé avec succès.')
        return response


# class ConversationView(LoginRequiredMixin, ListView):
#     model = Message
#     template_name = 'interactions/conversation.html'
#     context_object_name = 'messages'
#     paginate_by = 20
    
#     def get_queryset(self):
#         self.other_user = get_object_or_404(User, id=self.kwargs['user_id'])
        
#         # Récupère tous les messages entre les deux utilisateurs
#         messages = Message.objects.filter(
#             (Q(sender=self.request.user) & Q(recipient=self.other_user)) |
#             (Q(sender=self.other_user) & Q(recipient=self.request.user))
#         ).order_by('sent_at')
        
#         # Marquer les messages comme lus
#         unread_messages = messages.filter(
#             recipient=self.request.user,
#             is_read=False
#         )
        
#         # Mettre à jour les messages non lus
#         unread_messages.update(is_read=True)
        
#         # Mettre à jour le compteur de notifications
#         Notification.objects.filter(
#             user=self.request.user,
#             is_read=False
#         ).update(is_read=True)
        
#         return messages
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['other_user'] = self.other_user
#         context['form'] = MessageForm()
#         return context

class ConversationView(LoginRequiredMixin, ListView):
    template_name = 'interactions/conversation.html'
    context_object_name = 'messages'
    paginate_by = 50

    def get_queryset(self):
        if 'user_id' in self.kwargs:
            self.other_user = get_object_or_404(User, id=self.kwargs['user_id'])
            
            # Marquer les messages comme lus
            Message.objects.filter(
                sender=self.other_user,
                recipient=self.request.user,
                is_read=False
            ).update(is_read=True)
            
            return Message.objects.filter(
                Q(sender=self.request.user, recipient=self.other_user) |
                Q(sender=self.other_user, recipient=self.request.user)
            ).order_by('sent_at')
        return Message.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Récupérer l'utilisateur de la conversation si spécifié
        if hasattr(self, 'other_user'):
            context['other_user'] = self.other_user
        
        # Récupérer les conversations récentes avec le nombre de messages non lus
        conversations = []
        
        # Récupérer les utilisateurs avec qui l'utilisateur a échangé des messages
        sent_messages = Message.objects.filter(sender=user).values('recipient').distinct()
        received_messages = Message.objects.filter(recipient=user).values('sender').distinct()
        
        # Combiner et dédupliquer les utilisateurs
        user_ids = set()
        user_ids.update(msg['recipient'] for msg in sent_messages)
        user_ids.update(msg['sender'] for msg in received_messages)
        
        for user_id in user_ids:
            other_user = User.objects.get(id=user_id)
            
            # Dernier message échangé
            last_message = Message.objects.filter(
                Q(sender=user, recipient=other_user) |
                Q(sender=other_user, recipient=user)
            ).latest('sent_at')
            
            # Nombre de messages non lus
            unread_count = Message.objects.filter(
                sender=other_user,
                recipient=user,
                is_read=False
            ).count()
            
            conversations.append({
                'other_user': other_user,
                'last_message': last_message,
                'unread_count': unread_count
            })
        
        # Trier par date de dernier message (du plus récent au plus ancien)
        conversations.sort(key=lambda x: x['last_message'].sent_at, reverse=True)
        context['conversations'] = conversations
        
        # Si pas d'utilisateur spécifié mais qu'il y a des conversations, rediriger vers la première
        if 'other_user' not in context and conversations:
            return redirect('interactions:conversation', user_id=conversations[0]['other_user'].id)
            
        return context


def get_unread_count(request):
    """Renvoie le nombre de messages non lus en JSON"""
    if request.user.is_authenticated:
        count = Message.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'unread_count': count})
    return JsonResponse({'unread_count': 0})