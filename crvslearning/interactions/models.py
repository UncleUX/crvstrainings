from django.db import models
from django.utils import timezone
from django.db.models import Q
from shortuuidfield import ShortUUIDField
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('DM', 'Message direct'),
        ('GROUP', 'Groupe'),
    )
    
    roomId = ShortUUIDField(unique=True)
    type = models.CharField(max_length=10, choices=ROOM_TYPES, default='DM')
    members = models.ManyToManyField(User, related_name='interactions_chat_rooms')
    name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.roomId})"
        return f"Chat {self.roomId}"
    
    def get_last_message(self):
        return self.messages.order_by('-timestamp').first()
    
    def get_unread_count(self, user):
        return self.messages.filter(
            ~Q(sender=user),
            read_by__id__contains=user.id
        ).count()
        
    def get_other_member(self):
        """
        Pour une conversation DM, retourne l'autre membre de la conversation
        Utilise l'utilisateur actuel depuis le contexte de la requête
        """
        from django.contrib.auth import get_user
        from django.contrib.auth.models import AnonymousUser
        
        if self.type == 'DM':
            request = getattr(self, '_request', None)
            if request and not isinstance(request.user, AnonymousUser):
                return self.members.exclude(id=request.user.id).first()
        return None

class ChatMessage(models.Model):
    chat = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    read_by = models.ManyToManyField(User, related_name='interactions_read_messages', blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    def mark_as_read(self, user):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.read_by.add(user)
            self.save()
            return True
        return False

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('MESSAGE', 'Nouveau message'),
        ('MENTION', 'Mention'),
        ('SYSTEM', 'Système'),
    )
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='interactions_notifications'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='interactions_sent_notifications', 
        null=True, 
        blank=True
    )
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='MESSAGE')
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.username}"
    
    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.save()
            return True
        return False
    
    @classmethod
    def create_notification(cls, recipient, message, notification_type='MESSAGE', sender=None, url=None):
        return cls.objects.create(
            recipient=recipient,
            sender=sender,
            message=message,
            notification_type=notification_type,
            url=url
        )
