from django import forms
from django.forms import inlineformset_factory
from .models import Exercise, Choice

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct', 'order', 'explanation']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['question', 'order']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

# Formset for managing choices within the exercise form
ChoiceFormSet = inlineformset_factory(
    Exercise, 
    Choice, 
    form=ChoiceForm,
    extra=3,  # Number of empty choice forms to display
    min_num=2,  # Minimum number of choices required
    validate_min=True,
    can_delete=True
)
