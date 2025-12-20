from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Message(models.Model):
    sender = models.ForeignKey(
        User, 
        related_name='sms_sent_messages', 
        on_delete=models.CASCADE,
        verbose_name='expéditeur'
    )
    receiver = models.ForeignKey(
        User, 
        related_name='sms_received_messages', 
        on_delete=models.CASCADE,
        verbose_name='destinataire'
    )
    content = models.TextField(verbose_name='contenu')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='date d\'envoi')
    is_read = models.BooleanField(default=False, verbose_name='lu')

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'message'
        verbose_name_plural = 'messages'

    def __str__(self):
        return f'De {self.sender} à {self.receiver} - {self.timestamp}'
