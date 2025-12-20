# Vue pour le chat global
import json
from django.utils import timezone
from django.utils.dateformat import format
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import ChatRoomSerializer, ChatMessageSerializer, NotificationSerializer
from .models import ChatRoom, ChatMessage, Notification
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q
import logging
logger = logging.getLogger(__name__)

# Vues pour la messagerie
def inbox(request):
    """Affiche la boîte de réception de l'utilisateur"""
    user = request.user
    messages = ChatMessage.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).order_by('-timestamp')
    
    # Récupérer les conversations uniques
    conversations = {}
    for message in messages:
        other_user = message.sender if message.recipient == user else message.recipient
        if other_user.id not in conversations:
            conversations[other_user.id] = {
                'user': other_user,
                'last_message': message,
                'unread': ChatMessage.objects.filter(
                    recipient=user,
                    sender=other_user,
                    is_read=False
                ).count()
            }
    
    return render(request, 'interactions/inbox.html', {
        'conversations': conversations.values(),
    })

def compose(request, recipient_username=None):
    """Page pour composer un nouveau message"""
    user = request.user
    
    if request.method == 'POST':
        recipient_username = request.POST.get('recipient')
        content = request.POST.get('content')
        
        try:
            recipient = User.objects.get(username=recipient_username)
            
            # Créer ou récupérer la conversation
            room, created = ChatRoom.objects.get_or_create(
                type='DM',
                defaults={'name': f"Chat between {user.username} and {recipient.username}"}
            )
            
            # Ajouter les utilisateurs à la conversation si nécessaire
            if user not in room.members.all():
                room.members.add(user)
            if recipient not in room.members.all():
                room.members.add(recipient)
            
            # Créer le message
            message = ChatMessage.objects.create(
                room=room,
                sender=user,
                recipient=recipient,
                content=content
            )
            
            return redirect('interactions:conversation', user_id=recipient.id)
            
        except User.DoesNotExist:
            error = "L'utilisateur spécifié n'existe pas."
    else:
        error = None
    
    return render(request, 'interactions/compose.html', {
        'recipient_username': recipient_username,
        'error': error
    })

def conversation(request, user_id):
    """Affiche une conversation avec un utilisateur spécifique"""
    user = request.user
    other_user = get_object_or_404(User, id=user_id)
    
    # Marquer les messages comme lus
    ChatMessage.objects.filter(
        sender=other_user,
        recipient=user,
        is_read=False
    ).update(is_read=True)
    
    # Récupérer les messages
    messages = ChatMessage.objects.filter(
        (Q(sender=user) & Q(recipient=other_user)) |
        (Q(sender=other_user) & Q(recipient=user))
    ).order_by('timestamp')
    
    return render(request, 'interactions/conversation.html', {
        'other_user': other_user,
        'messages': messages
    })

def send_message(request, recipient_id):
    """API pour envoyer un message"""
    if request.method == 'POST':
        recipient = get_object_or_404(User, id=recipient_id)
        content = request.POST.get('content', '').strip()
        
        if content:
            # Créer ou récupérer la conversation
            room, created = ChatRoom.objects.get_or_create(
                type='DM',
                defaults={'name': f"Chat between {request.user.username} and {recipient.username}"}
            )
            
            # Ajouter les utilisateurs à la conversation si nécessaire
            if request.user not in room.members.all():
                room.members.add(request.user)
            if recipient not in room.members.all():
                room.members.add(recipient)
            
            # Créer le message
            message = ChatMessage.objects.create(
                room=room,
                sender=request.user,
                recipient=recipient,
                content=content
            )
            
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'sender': message.sender.username
                }
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# Vues pour les notifications
def notifications(request):
    """Affiche les notifications de l'utilisateur"""
    user = request.user
    notifications = Notification.objects.filter(recipient=user).order_by('-timestamp')
    
    return render(request, 'interactions/notifications.html', {
        'notifications': notifications
    })

def mark_notification_read(request, notification_id):
    """Marque une notification comme lue"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect(notification.get_absolute_url())

def mark_all_notifications_read(request):
    """Marque toutes les notifications comme lues"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('interactions:notifications')

User = get_user_model()

class GlobalChatView(LoginRequiredMixin, TemplateView):
    template_name = 'interactions/chatgobal.html'
    login_url = '/users/login/'
    redirect_field_name = 'next'
    
    def dispatch(self, request, *args, **kwargs):
        logger.info(f"Début de la requête - Utilisateur authentifié : {request.user.is_authenticated}")
        logger.info(f"Session : {dict(request.session)}")
        logger.info(f"Headers : {dict(request.headers)}")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"Utilisateur dans get_context_data : {user} (authentifié: {user.is_authenticated})")
        
        # Récupérer les informations de l'utilisateur actuel
        context['current_user'] = user
        
        # Récupérer les utilisateurs disponibles pour le chat
        users = User.objects.exclude(id=user.id).all()
        
        # Préparer les données des utilisateurs
        users_data = []
        for u in users:
            users_data.append({
                'id': u.id,
                'username': u.username,
                'name': u.get_full_name() or u.username,
                'avatar': f'/media/{u.avatar}' if u.avatar else '/static/img/default-avatar.png',
                'is_online': u.is_online,
                'unread': 0
            })
        
        # Récupérer les conversations existantes
        conversations = ChatRoom.objects.filter(members=user).prefetch_related('members', 'messages')
        conversations_data = []
        
        for conv in conversations:
            other_member = conv.members.exclude(id=user.id).first()
            if other_member:
                last_message = conv.messages.order_by('-timestamp').first()
                conversations_data.append({
                    'id': conv.id,
                    'other_user': {
                        'id': other_member.id,
                        'username': other_member.username,
                        'name': other_member.get_full_name() or other_member.username,
                        'avatar': f'/media/{other_member.avatar}' if other_member.avatar else '/static/img/default-avatar.png',
                        'is_online': other_member.is_online
                    },
                    'last_message': {
                        'content': last_message.content if last_message else '',
                        'timestamp': format(last_message.timestamp, 'd/m/Y H:i') if last_message else '',
                        'is_read': last_message.is_read if last_message else True
                    } if last_message else None,
                    'unread_count': conv.messages.filter(recipient=user, is_read=False).count()
                })
        
        # Mettre à jour le contexte
        context.update({
            'users_data': json.dumps(users_data, default=str),
            'conversations_data': json.dumps(conversations_data, default=str),
            'current_user_data': json.dumps({
                'id': user.id,
                'username': user.username,
                'name': user.get_full_name() or user.username,
                'avatar': f'/media/{user.avatar}' if user.avatar else '/static/img/default-avatar.png',
                'first_name': user.first_name,
                'last_name': user.last_name
            }, default=str),
            'websocket_url': f"ws://{self.request.get_host()}/ws/chat/"
        })
        return context

# Vues API pour le chat en temps réel
class ChatRoomView(generics.ListCreateAPIView):
    """API pour lister et créer des salles de chat"""
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatRoom.objects.filter(members=self.request.user)
    
    def perform_create(self, serializer):
        room = serializer.save()
        room.members.add(self.request.user)

class ChatRoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API pour récupérer, mettre à jour et supprimer une salle de chat"""
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatRoom.objects.filter(members=self.request.user)

class MessageListCreateView(generics.ListCreateAPIView):
    """API pour lister et créer des messages"""
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return ChatMessage.objects.filter(
            chat_id=room_id,
            chat__members=self.request.user
        ).order_by('timestamp')
    
    def perform_create(self, serializer):
        room_id = self.kwargs.get('room_id')
        room = get_object_or_404(ChatRoom, id=room_id, members=self.request.user)
        serializer.save(sender=self.request.user, chat=room)

class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API pour récupérer, mettre à jour et supprimer un message"""
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatMessage.objects.filter(
            sender=self.request.user,
            chat__members=self.request.user
        )

class NotificationListView(generics.ListAPIView):
    """API pour lister les notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API pour récupérer, mettre à jour et supprimer une notification"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def perform_update(self, serializer):
        # Marquer comme lu lors de la mise à jour
        serializer.save(read=True, read_at=timezone.now())

class MessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, room_id):
        chat_room = get_object_or_404(ChatRoom, roomId=room_id, members=request.user)
        serializer = ChatRoomSerializer(chat_room, context={'request': request})
        messages = chat_room.messages.all().order_by('timestamp')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    def post(self, request, room_id):
        chat_room = get_object_or_404(ChatRoom, roomId=room_id, members=request.user)
        
        serializer = ChatMessageSerializer(data=request.data, context={
            'request': request,
            'chat_room': chat_room
        })
        
        if serializer.is_valid():
            message = serializer.save()
            
            # Mettre à jour la date de mise à jour de la conversation
            chat_room.updated_at = timezone.now()
            chat_room.save()
            
            # Créer des notifications pour les destinataires
            for recipient in chat_room.members.exclude(id=request.user.id):
                Notification.create_notification(
                    recipient=recipient,
                    sender=request.user,
                    message=f"Nouveau message de {request.user.get_full_name() or request.user.username}",
                    notification_type='MESSAGE',
                    url=reverse('interactions:conversation', args=[chat_room.roomId])
                )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request, notification_id=None):
        if notification_id:
            # Marquer une notification spécifique comme lue
            notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
            notification.mark_as_read()
            return Response({'status': 'success'})
        
        # Marquer toutes les notifications comme lues
        Notification.objects.filter(recipient=request.user, read=False).update(read=True)
        return Response({'status': 'success'})
