from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from .models import Message

User = get_user_model()

@login_required
def inbox(request):
    # Récupérer tous les utilisateurs sauf l'utilisateur actuel
    users = User.objects.exclude(id=request.user.id).order_by('first_name', 'username')
    
    # Récupérer les utilisateurs avec qui l'utilisateur actuel a déjà discuté
    chatted_users = User.objects.filter(
        Q(sms_sent_messages__receiver=request.user) | 
        Q(sms_received_messages__sender=request.user)
    ).distinct()
    
    # Marquer les messages non lus comme lus
    Message.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
    
    # Vérifier s'il y a une recherche
    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    return render(request, 'sms/inbox.html', {
        'users': users,
        'chatted_users': chatted_users,
        'search_query': query or ''
    })

@login_required
def chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    # Récupérer les messages entre les deux utilisateurs
    messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) |
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by('timestamp')
    
    # Marquer les messages comme lus
    messages.filter(receiver=request.user, is_read=False).update(is_read=True)
    
    return render(request, 'sms/chat.html', {
        'other_user': other_user,
        'messages': messages,
    })

@login_required
def send_message(request, user_id):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            receiver = get_object_or_404(User, id=user_id)
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'timestamp': message.timestamp.isoformat(),
                        'sender': message.sender.id
                    }
                })
    
    return JsonResponse({'success': False})

@login_required
def get_new_messages(request, user_id, last_message_id):
    other_user = get_object_or_404(User, id=user_id)
    
    messages = Message.objects.filter(
        Q(id__gt=last_message_id) &
        (Q(sender=other_user, receiver=request.user) | 
         Q(sender=request.user, receiver=other_user))
    ).order_by('timestamp')
    
    # Marquer uniquement les messages reçus comme lus
    messages.filter(receiver=request.user, is_read=False).update(is_read=True)
    
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'sender': msg.sender.id
    } for msg in messages]
    
    return JsonResponse(messages_data, safe=False)
