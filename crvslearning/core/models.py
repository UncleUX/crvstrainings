from django.conf import settings
from django.db import models
from django.db.models import (Model, TextField, DateTimeField, ForeignKey,
                              CASCADE, BooleanField, Q)
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from shortuuidfield import ShortUUIDField
from django.contrib.auth import get_user_model

# Utilisation du modèle d'utilisateur personnalisé
User = get_user_model()


class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('DM', 'Message direct'),
        ('GROUP', 'Groupe'),
    )
    
    roomId = ShortUUIDField(unique=True)
    type = models.CharField(max_length=10, choices=ROOM_TYPES, default='DM')
    members = models.ManyToManyField(User, related_name='chat_rooms')
    name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'salle de discussion'
        verbose_name_plural = 'salles de discussion'

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.roomId})"
        return f"Chat {self.roomId}"
    
    def get_last_message(self):
        return self.messages.order_by('-timestamp').first()
    
    def get_unread_count(self, user):
        return self.messages.filter(
            ~Q(sender=user),
            read=False
        ).count()
        
    def get_other_member(self, user):
        """
        Pour une conversation DM, retourne l'autre membre de la conversation
        """
        if self.type == 'DM':
            return self.members.exclude(id=user.id).first()
        return None


class MessageModel(Model):
    """
    Modèle représentant un message de chat. Contient un expéditeur, un destinataire,
    un horodatage et le contenu du message.
    """
    chat = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    user = ForeignKey(User, on_delete=CASCADE, verbose_name='expéditeur',
                     related_name='core_sent_messages', db_index=True)
    recipient = ForeignKey(User, on_delete=CASCADE, verbose_name='destinataire',
                         related_name='core_received_messages', db_index=True, null=True, blank=True)
    timestamp = DateTimeField('date d\'envoi', auto_now_add=True, 
                            editable=False, db_index=True)
    body = TextField('contenu')
    read = BooleanField('lu', default=False, db_index=True)
    read_at = DateTimeField('date de lecture', null=True, blank=True)
    read_by = models.ManyToManyField(User, related_name='core_read_messages', blank=True)

    def __str__(self):
        return f"{self.user.username}: {self.body[:50]}"

    def characters(self):
        """
        Toy function to count body characters.
        :return: body's char number
        """
        return len(self.body)

    def notify_ws_clients(self):
        """
        Informe les clients qu'un nouveau message est disponible via WebSocket.
        """
        from django.core.serializers.json import DjangoJSONEncoder
        import json
        
        # Récupérer les informations de l'expéditeur et du destinataire
        user_data = {
            'id': self.user.id,
            'username': self.user.username,
            'avatar': self.user.get_avatar_display() if hasattr(self.user, 'get_avatar_display') else None,
            'is_online': self.user.is_online if hasattr(self.user, 'is_online') else False
        }
        
        recipient_data = {
            'id': self.recipient.id,
            'username': self.recipient.username,
            'avatar': self.recipient.get_avatar_display() if hasattr(self.recipient, 'get_avatar_display') else None,
            'is_online': self.recipient.is_online if hasattr(self.recipient, 'is_online') else False
        }
        
        # Créer un dictionnaire avec les données du message
        message_data = {
            'id': self.id,
            'user': user_data,
            'recipient': recipient_data,
            'body': self.body,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'type': 'chat_message'
        }
        
        # Créer la notification
        notification = {
            'type': 'chat_message',
            'message': message_data
        }
        
        # Envoyer la notification via le canal
        channel_layer = get_channel_layer()
        
        # Envoyer à l'expéditeur
        sender_group = f"user_{self.user.id}"
        async_to_sync(channel_layer.group_send)(sender_group, notification)
        
        # Envoyer au destinataire (si différent de l'expéditeur)
        if self.user.id != self.recipient.id:
            recipient_group = f"user_{self.recipient.id}"
            async_to_sync(channel_layer.group_send)(recipient_group, notification)

    def save(self, *args, **kwargs):
        """
        Nettoie le message, l'enregistre et notifie le destinataire via WebSocket
        si c'est un nouveau message.
        """
        is_new = self.id is None
        self.body = self.body.strip()  # Supprime les espaces superflus
        
        # Si le message est marqué comme lu et que c'est une mise à jour
        if not is_new and 'read' in kwargs.get('update_fields', []) and self.read and not self.read_at:
            self.read_at = timezone.now()
            
        super().save(*args, **kwargs)
        
        # Mettre à jour la date de mise à jour de la salle de discussion
        if self.chat:
            self.chat.updated_at = timezone.now()
            self.chat.save(update_fields=['updated_at'])
        
        # Notifier les clients uniquement pour les nouveaux messages
        if is_new:
            self.notify_ws_clients()
    
    def mark_as_read(self, user):
        """Marque le message comme lu par un utilisateur spécifique"""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.read_by.add(user)
            self.save(update_fields=['read', 'read_at'])
            return True
        return False

    class Meta:
        app_label = 'core'
        verbose_name = 'message'
        verbose_name_plural = 'messages'
        ordering = ('-timestamp',)
        indexes = [
            models.Index(fields=['user', 'recipient', 'read']),
            models.Index(fields=['recipient', 'read']),
            models.Index(fields=['chat', 'timestamp']),
        ]
        
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('core:message_detail', kwargs={'pk': self.pk})
