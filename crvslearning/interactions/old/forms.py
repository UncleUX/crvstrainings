# interactions/forms.py
from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si un utilisateur est connecté, filtrer les destinataires possibles
        if self.user and self.user.is_authenticated:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['recipient'].queryset = User.objects.exclude(id=self.user.id)
            self.fields['recipient'].label = "Destinataire"
            self.fields['subject'].label = "Sujet"
            self.fields['body'].label = "Message"