from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    # Définition personnalisée du champ role avec uniquement les rôles autorisés
    role = forms.ChoiceField(
        label='Rôle',
        choices=(
            ('learner', 'Apprenant'),
            ('trainer', 'Formateur')
        ),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='learner',
        help_text='Choisissez votre rôle principal dans la plateforme.'
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des champs
        self.fields['username'].help_text = 'Obligatoire. 150 caractères maximum. Lettres, chiffres et @/./+/-/_ uniquement.'
        self.fields['email'].required = True
        self.fields['role'].label = 'Je m\'inscris en tant que :'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'bio', 'avatar', 'cover')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
