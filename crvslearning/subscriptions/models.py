from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Subscription(models.Model):
    """Modèle pour gérer les abonnements des apprenants aux formateurs"""
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=_('Abonné')
    )
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name=_('Formateur')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'abonnement"))
    is_active = models.BooleanField(default=True, verbose_name=_('Abonnement actif'))

    class Meta:
        unique_together = ('subscriber', 'trainer')
        verbose_name = _('Abonnement')
        verbose_name_plural = _('Abonnements')

    def __str__(self):
        return f"{self.subscriber} suit {self.trainer}"
