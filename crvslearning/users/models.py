from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('learner', _('Apprenant')),
        ('trainer', _('Formateur')),
        ('admin', _('Administrateur')),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='learner')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    last_seen = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_online(self):
        from django.utils import timezone
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 300

    def get_avatar_url(self):
        """
        Return avatar URL if exists, else None.
        """
        if self.avatar and hasattr(self.avatar, 'url'):
            try:
                return self.avatar.url
            except ValueError:
                return None
        return None

    def get_avatar_display(self, default_color='#3b82f6'):
        """
        Returns avatar display info:
        - If image → return URL
        - Else → return initial with generated color
        """
        avatar_url = self.get_avatar_url()
        if avatar_url:
            return {
                'type': 'image',
                'url': avatar_url,
                'alt': f"Photo de profil de {self.username}"
            }

        # Generate a background color based on username
        import hashlib
        if self.username:
            hue = int(hashlib.md5(self.username.encode()).hexdigest()[:8], 16) % 360
            bg_color = f'hsl({hue}, 70%, 60%)'
        else:
            bg_color = default_color

        # Get initial
        initial = (self.first_name[0] if self.first_name else self.username[0]).upper()

        return {
            'type': 'initial',
            'text': initial,
            'bg_color': bg_color,
            'color': '#ffffff',
            'alt': f"Initiale de {self.username}"
        }

    def get_unread_messages(self):
        """
        Return user's unread messages
        """
        if hasattr(self, 'received_messages'):
            return self.received_messages.filter(read=False)
        return self.receivedmessage_set.filter(read=False)

    def get_unread_messages_count(self):
        """
        Return count of unread messages
        """
        return self.get_unread_messages().count()
